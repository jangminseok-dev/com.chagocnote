import httpx
import pytest

from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


def _http(app_id=1234, me_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer kakao-token"
        if request.url.path == "/v1/user/access_token_info":
            return httpx.Response(200, json={"id": 99, "app_id": app_id})
        if request.url.path == "/v2/user/me":
            return httpx.Response(me_status, json={
                "id": 99,
                "kakao_account": {
                    "email": "a@example.com",
                    "profile": {"nickname": "두부 보호자", "profile_image_url": "https://img/1.jpg"},
                },
            })
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_카카오가_확인해_준_프로필을_돌려준다():
    profile = await KakaoIdentityStrategy("1234", _http()).verify(SocialCredentials(token="kakao-token"))
    assert profile.provider is Provider.KAKAO
    assert profile.provider_user_id == "99"
    assert profile.display_name == "두부 보호자"
    assert profile.email == "a@example.com"
    assert profile.provider_refresh_token is None


async def test_다른_앱에서_발급된_토큰은_거절한다():
    with pytest.raises(ProviderVerificationError):
        await KakaoIdentityStrategy("1234", _http(app_id=5678)).verify(SocialCredentials(token="kakao-token"))


async def test_카카오가_사용자_조회를_거절하면_실패한다():
    with pytest.raises(ProviderVerificationError):
        await KakaoIdentityStrategy("1234", _http(me_status=401)).verify(SocialCredentials(token="kakao-token"))
