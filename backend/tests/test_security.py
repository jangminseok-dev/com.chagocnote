from datetime import datetime, timedelta, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import text

import core.security as security
from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
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


@pytest.fixture
def issuer(monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    return JwtTokenIssuer(private_pem, ttl_seconds=900)


async def test_정상_계정은_유저_ID를_돌려준다(db_session, issuer):
    await _insert_user(db_session, id=1)
    token = issuer.issue_access(1).token
    assert await security.get_current_user_id(db=db_session, credentials=_bearer(token)) == 1


async def test_토큰이_없으면_401이다(db_session, issuer):
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(db=db_session, credentials=None)
    assert (exc.value.status_code, exc.value.code) == (401, "UNAUTHENTICATED")


async def test_정지된_계정은_이미_발급된_토큰으로도_403이다(db_session, issuer):
    await _insert_user(db_session, id=2, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(db=db_session, credentials=_bearer(issuer.issue_access(2).token))
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_401이다(db_session, issuer):
    await _insert_user(db_session, id=3, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(db=db_session, credentials=_bearer(issuer.issue_access(3).token))
    assert exc.value.status_code == 401


def test_만료_시각이_없는_토큰은_받지_않는다():
    private_pem, public_pem, _ = make_rsa_keypair()
    token = jwt.encode({"sub": "1", "typ": "access"}, private_pem, algorithm="RS256")
    with pytest.raises(security.InvalidAccessToken):
        security.decode_access_token(token, public_pem)


async def test_방금_로그인한_토큰은_최근_로그인으로_통과한다(db_session, issuer):
    await _insert_user(db_session, id=11)
    token = issuer.issue_access(11, fresh_login=True).token
    recent = await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert recent.user_id == 11
    assert recent.auth_time > 0


async def test_갱신으로_받은_토큰은_REAUTH_REQUIRED_다(db_session, issuer):
    await _insert_user(db_session, id=12)
    token = issuer.issue_access(12).token   # auth_time 없음 = 갱신이 발급한 토큰
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_로그인한_지_오래된_토큰은_403_이다(db_session, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    await _insert_user(db_session, id=13)
    long_ago = lambda: datetime.now(timezone.utc) - timedelta(seconds=security.RECENT_LOGIN_SECONDS + 1)
    # 만료는 아직 멀었지만(ttl 900초) 로그인한 지 301초가 지났다.
    token = JwtTokenIssuer(private_pem, ttl_seconds=900, now=long_ago).issue_access(13, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_경계_안쪽의_토큰은_통과한다(db_session, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    await _insert_user(db_session, id=14)
    almost = lambda: datetime.now(timezone.utc) - timedelta(seconds=security.RECENT_LOGIN_SECONDS - 5)
    token = JwtTokenIssuer(private_pem, ttl_seconds=900, now=almost).issue_access(14, fresh_login=True).token
    assert (await security.require_recent_login(db=db_session, credentials=_bearer(token))).user_id == 14


async def test_정지된_계정은_최근_로그인이어도_403_ACCOUNT_SUSPENDED_다(db_session, issuer):
    await _insert_user(db_session, id=15, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    token = issuer.issue_access(15, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_최근_로그인이어도_401_이다(db_session, issuer):
    await _insert_user(db_session, id=16, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    token = issuer.issue_access(16, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert exc.value.status_code == 401


def _freeze_now(monkeypatch, at):
    monkeypatch.setattr(security, "_utcnow", lambda: at)


async def test_로그인한_지_정확히_300초면_통과하고_301초면_403_이다(db_session, issuer, monkeypatch):
    await _insert_user(db_session, id=17)
    logged_in = datetime.now(timezone.utc).replace(microsecond=0)
    auth_time = int(logged_in.timestamp())
    token = issuer.issue_access(17, auth_time=auth_time).token

    _freeze_now(monkeypatch, logged_in + timedelta(seconds=security.RECENT_LOGIN_SECONDS))
    recent = await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert recent.auth_time == auth_time

    _freeze_now(monkeypatch, logged_in + timedelta(seconds=security.RECENT_LOGIN_SECONDS + 1))
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_로그인_시각이_60초_넘게_미래면_403_이다(db_session, issuer, monkeypatch):
    await _insert_user(db_session, id=18)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _freeze_now(monkeypatch, now)
    at_limit = issuer.issue_access(18, auth_time=int(now.timestamp()) + 60).token
    assert (await security.require_recent_login(db=db_session, credentials=_bearer(at_limit))).user_id == 18

    too_far = issuer.issue_access(18, auth_time=int(now.timestamp()) + 61).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(too_far))
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")
