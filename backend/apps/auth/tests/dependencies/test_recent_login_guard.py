"""재인증 가드 — 실제 토큰과 users 표로 확인한다. 판정 규칙 자체는 domain/test_recent_login.py 가 본다."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text

import auth.dependencies.recent_login_guard as guard
import core.security as security
from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.domain.services.recent_login import RECENT_LOGIN_SECONDS
from auth.tests.helpers.keys import make_rsa_keypair
from core.http_errors import ApiError

pytestmark = pytest.mark.integration


async def _insert_user(session, **columns):
    await session.execute(
        text(
            "INSERT INTO users (id, display_name, suspended_at, deleted_at) "
            "VALUES (:id, '테스트', :suspended_at, :deleted_at)"
        ),
        {"suspended_at": None, "deleted_at": None, **columns},
    )


def _bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def _require(db, token):
    return await guard.require_recent_login(await security.get_access_claims(db=db, credentials=_bearer(token)))


@pytest.fixture
def issuer(monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    return JwtTokenIssuer(private_pem, ttl_seconds=900)


async def test_방금_로그인한_토큰은_최근_로그인으로_통과한다(db_session, issuer):
    await _insert_user(db_session, id=11)
    recent = await _require(db_session, issuer.issue_access(11, fresh_login=True).token)
    assert recent.user_id == 11
    assert recent.auth_time > 0


async def test_갱신으로_받은_토큰은_REAUTH_REQUIRED_다(db_session, issuer):
    await _insert_user(db_session, id=12)
    with pytest.raises(ApiError) as exc:
        await _require(db_session, issuer.issue_access(12).token)   # auth_time 없음 = 갱신이 발급한 토큰
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_로그인한_지_오래된_토큰은_403_이다(db_session, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    await _insert_user(db_session, id=13)
    long_ago = lambda: datetime.now(timezone.utc) - timedelta(seconds=RECENT_LOGIN_SECONDS + 1)
    # 만료는 아직 멀었지만(ttl 900초) 로그인한 지 301초가 지났다.
    token = JwtTokenIssuer(private_pem, ttl_seconds=900, now=long_ago).issue_access(13, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await _require(db_session, token)
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_정지된_계정은_최근_로그인이어도_403_ACCOUNT_SUSPENDED_다(db_session, issuer):
    await _insert_user(db_session, id=15, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await _require(db_session, issuer.issue_access(15, fresh_login=True).token)
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_최근_로그인이어도_401_이다(db_session, issuer):
    await _insert_user(db_session, id=16, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await _require(db_session, issuer.issue_access(16, fresh_login=True).token)
    assert exc.value.status_code == 401


async def test_가드는_지금_시각으로_판정한다(db_session, issuer, monkeypatch):
    """경계값 자체는 도메인 테스트가 본다. 여기서는 가드가 _utcnow 를 쓰는지만 못 박는다."""
    await _insert_user(db_session, id=17)
    logged_in = datetime.now(timezone.utc).replace(microsecond=0)
    token = issuer.issue_access(17, auth_time=int(logged_in.timestamp())).token
    monkeypatch.setattr(guard, "_utcnow", lambda: logged_in + timedelta(seconds=RECENT_LOGIN_SECONDS))
    assert (await _require(db_session, token)).auth_time == int(logged_in.timestamp())
    monkeypatch.setattr(guard, "_utcnow", lambda: logged_in + timedelta(seconds=RECENT_LOGIN_SECONDS + 1))
    with pytest.raises(ApiError):
        await _require(db_session, token)
