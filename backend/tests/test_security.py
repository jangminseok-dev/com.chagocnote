from datetime import datetime, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials
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
    assert await security.get_current_user_id(_bearer(token), db_session) == 1


async def test_토큰이_없으면_401이다(db_session, issuer):
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(None, db_session)
    assert (exc.value.status_code, exc.value.code) == (401, "UNAUTHENTICATED")


async def test_정지된_계정은_이미_발급된_토큰으로도_403이다(db_session, issuer):
    await _insert_user(db_session, id=2, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(_bearer(issuer.issue_access(2).token), db_session)
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_401이다(db_session, issuer):
    await _insert_user(db_session, id=3, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(_bearer(issuer.issue_access(3).token), db_session)
    assert exc.value.status_code == 401
