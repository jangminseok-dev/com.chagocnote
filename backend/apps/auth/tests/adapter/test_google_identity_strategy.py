import time

import pytest
from jose import jwt

from auth.adapter.outbound.strategy.google_identity_strategy import GoogleIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.tests.helpers.keys import make_rsa_keypair

PRIVATE_PEM, _, JWK = make_rsa_keypair(kid="google-kid")


async def _jwks():
    return {"keys": [JWK]}


def _id_token(**overrides):
    claims = {
        "iss": "https://accounts.google.com", "aud": "ios-client-id", "sub": "google-7",
        "email": "a@example.com", "name": "두부 보호자", "picture": "https://img/g.jpg",
        "exp": int(time.time()) + 600, **overrides,
    }
    return jwt.encode(claims, PRIVATE_PEM, algorithm="RS256", headers={"kid": "google-kid"})


def _strategy():
    return GoogleIdentityStrategy(("ios-client-id", "android-client-id"), _jwks)


async def test_서명과_대상_앱이_맞으면_프로필을_돌려준다():
    profile = await _strategy().verify(SocialCredentials(token=_id_token()))
    assert profile.provider is Provider.GOOGLE
    assert profile.provider_user_id == "google-7"
    assert profile.display_name == "두부 보호자"
    assert profile.profile_image_url == "https://img/g.jpg"


async def test_안드로이드_클라이언트_ID_도_받아들인다():
    profile = await _strategy().verify(SocialCredentials(token=_id_token(aud="android-client-id")))
    assert profile.provider_user_id == "google-7"


async def test_다른_앱을_대상으로_한_토큰은_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(aud="someone-else")))


async def test_발급자가_구글이_아니면_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(iss="https://evil.example")))


async def test_다른_키로_서명한_토큰은_거절한다():
    other_private, _, _ = make_rsa_keypair(kid="google-kid")
    forged = jwt.encode(
        {"iss": "https://accounts.google.com", "aud": "ios-client-id", "sub": "x",
         "exp": int(time.time()) + 600},
        other_private, algorithm="RS256", headers={"kid": "google-kid"},
    )
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=forged))
