import httpx
import pytest

from auth.adapter.outbound.strategy.apple_identity_strategy import AppleIdentityStrategy
from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.adapter.outbound.strategy.google_identity_strategy import GoogleIdentityStrategy
from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.domain.errors import ProviderRevokeError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.tests.helpers.keys import make_ec_private_pem


def _recording_http(status=200):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), dict(request.headers), dict(httpx.QueryParams(request.content.decode()))))
        return httpx.Response(status, json={})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), seen


def _kakao(identity_id="99"):
    return IdentityRevocation(Provider.KAKAO, identity_id, None)


def _apple(token="apple-refresh"):
    return IdentityRevocation(Provider.APPLE, "apple-1", token)


async def _no_jwks():
    return {"keys": []}


def _apple_strategy(http):
    return AppleIdentityStrategy(
        bundle_id="com.chagocnote.app", team_id="TEAM123456", key_id="KEY1234567",
        private_key_pem=make_ec_private_pem(), http=http, fetch_jwks=_no_jwks,
    )


async def test_카카오는_어드민_키로_그_사용자의_연결을_끊는다():
    http, seen = _recording_http()
    await KakaoIdentityStrategy("1234", http, admin_key="admin-key").revoke(_kakao())
    url, headers, form = seen[0]
    assert url == "https://kapi.kakao.com/v1/user/unlink"
    assert headers["authorization"] == "KakaoAK admin-key"
    assert form == {"target_id_type": "user_id", "target_id": "99"}


async def test_카카오_어드민_키가_없으면_끊지_못한다():
    http, seen = _recording_http()
    with pytest.raises(ProviderRevokeError):
        await KakaoIdentityStrategy("1234", http).revoke(_kakao())
    assert seen == []


async def test_카카오가_거절하면_ProviderRevokeError_다():
    http, _ = _recording_http(status=401)
    with pytest.raises(ProviderRevokeError):
        await KakaoIdentityStrategy("1234", http, admin_key="admin-key").revoke(_kakao())


async def test_Apple_은_저장해_둔_리프레시_토큰을_폐기한다():
    http, seen = _recording_http()
    await _apple_strategy(http).revoke(_apple())
    url, _, form = seen[0]
    assert url == "https://appleid.apple.com/auth/revoke"
    assert form["client_id"] == "com.chagocnote.app"
    assert (form["token"], form["token_type_hint"]) == ("apple-refresh", "refresh_token")
    assert form["client_secret"]


async def test_Apple_토큰이_없으면_끊지_못한다():
    http, seen = _recording_http()
    with pytest.raises(ProviderRevokeError):
        await _apple_strategy(http).revoke(_apple(token=None))
    assert seen == []


async def test_Apple_이_거절하면_ProviderRevokeError_다():
    http, _ = _recording_http(status=400)
    with pytest.raises(ProviderRevokeError):
        await _apple_strategy(http).revoke(_apple())


async def test_네트워크_오류도_ProviderRevokeError_다():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("연결 실패")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderRevokeError):
        await KakaoIdentityStrategy("1234", http, admin_key="admin-key").revoke(_kakao())


async def test_구글과_dev_는_서버에서_할_일이_없다():
    await GoogleIdentityStrategy(("client",), _no_jwks).revoke(
        IdentityRevocation(Provider.GOOGLE, "google-7", None)
    )
    await DevIdentityStrategy().revoke(IdentityRevocation(Provider.DEV, "someone", None))
