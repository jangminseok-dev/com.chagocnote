import hashlib
import time

import httpx
import pytest
from jose import jwt

from auth.adapter.outbound.strategy.apple_identity_strategy import AppleIdentityStrategy
from auth.domain.errors import ProviderRevokeError, ProviderVerificationError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.tests.helpers.keys import make_ec_private_pem, make_rsa_keypair

APPLE_PRIVATE_PEM, _, APPLE_JWK = make_rsa_keypair(kid="apple-kid")
RAW_NONCE = "raw-nonce-from-app"


async def _jwks():
    return {"keys": [APPLE_JWK]}


def _id_token(**overrides):
    claims = {
        "iss": "https://appleid.apple.com", "aud": "com.chagocnote.app", "sub": "apple-1",
        "email": "relay@privaterelay.appleid.com",
        "nonce": hashlib.sha256(RAW_NONCE.encode()).hexdigest(),
        "exp": int(time.time()) + 600, **overrides,
    }
    return jwt.encode(claims, APPLE_PRIVATE_PEM, algorithm="RS256", headers={"kid": "apple-kid"})


def _strategy(exchange_status=200, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(exchange_status, json={"refresh_token": "apple-refresh"})

    return AppleIdentityStrategy(
        bundle_id="com.chagocnote.app", team_id="TEAM123456", key_id="KEY1234567",
        private_key_pem=make_ec_private_pem(),
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        fetch_jwks=_jwks,
    )


async def test_ID_토큰을_검증하고_인가_코드를_리프레시_토큰으로_바꾼다():
    seen = []
    profile = await _strategy(seen=seen).verify(SocialCredentials(
        token=_id_token(), authorization_code="auth-code", nonce=RAW_NONCE, display_name="두부 보호자",
    ))
    assert profile.provider is Provider.APPLE
    assert profile.provider_user_id == "apple-1"
    assert profile.display_name == "두부 보호자"
    assert profile.provider_refresh_token == "apple-refresh"
    assert seen[0]["code"] == "auth-code"
    assert seen[0]["client_id"] == "com.chagocnote.app"
    assert seen[0]["grant_type"] == "authorization_code"
    header = jwt.get_unverified_header(seen[0]["client_secret"])
    assert (header["alg"], header["kid"]) == ("ES256", "KEY1234567")


async def test_인가_코드가_없으면_교환하지_않는다():
    profile = await _strategy().verify(SocialCredentials(token=_id_token(), nonce=RAW_NONCE))
    assert profile.provider_refresh_token is None


async def test_nonce_가_다르면_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(), nonce="another-nonce"))


async def test_다른_앱을_대상으로_한_토큰은_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(aud="com.other.app"), nonce=RAW_NONCE))


async def test_코드_교환이_실패하면_로그인도_실패한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy(exchange_status=400).verify(
            SocialCredentials(token=_id_token(), authorization_code="bad", nonce=RAW_NONCE)
        )


async def test_저장된_토큰이_없으면_Apple_을_부르지_않고_거절한다():
    """복호화 실패로 provider_refresh_token 이 None 인 신원이 여기로 올 수 있다.
    Apple 에 빈 토큰으로 폐기를 요청하지 않고, 조용히 거절만 한다."""
    seen = []
    with pytest.raises(ProviderRevokeError):
        await _strategy(seen=seen).revoke(IdentityRevocation(Provider.APPLE, "apple-1", None))
    assert seen == []
