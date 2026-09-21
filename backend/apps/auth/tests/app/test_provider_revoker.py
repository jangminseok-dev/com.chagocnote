import logging

from auth.app.services.provider_revoker import ProviderRevoker
from auth.domain.errors import ProviderRevokeError, UnsupportedProviderError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider


class _StubProvider:
    def __init__(self, fail=False, unexpected_error=None):
        self.fail = fail
        self.unexpected_error = unexpected_error
        self.revoked = []

    async def revoke(self, identity):
        if self.unexpected_error is not None:
            raise self.unexpected_error
        if self.fail:
            raise ProviderRevokeError("카카오가 거절했습니다.")
        self.revoked.append(identity.provider_user_id)


class _StubResolver:
    def __init__(self, providers):
        self.providers = providers

    def resolve(self, provider):
        if provider not in self.providers:
            raise UnsupportedProviderError(f"{provider.value} 로그인은 지금 사용할 수 없습니다.")
        return self.providers[provider]


async def test_신원마다_그_제공자에게_연결을_끊으라고_한다():
    kakao, apple = _StubProvider(), _StubProvider()
    revoker = ProviderRevoker(_StubResolver({Provider.KAKAO: kakao, Provider.APPLE: apple}))
    await revoker.revoke_all([
        IdentityRevocation(Provider.KAKAO, "kakao-1", None),
        IdentityRevocation(Provider.APPLE, "apple-1", "secret-refresh-token"),
    ])
    assert (kakao.revoked, apple.revoked) == (["kakao-1"], ["apple-1"])


async def test_한_제공자가_실패해도_나머지는_끊고_로그에_토큰을_남기지_않는다(caplog):
    apple = _StubProvider()
    revoker = ProviderRevoker(_StubResolver({Provider.KAKAO: _StubProvider(fail=True), Provider.APPLE: apple}))
    with caplog.at_level(logging.WARNING):
        await revoker.revoke_all([
            IdentityRevocation(Provider.KAKAO, "kakao-1", None),
            IdentityRevocation(Provider.GOOGLE, "google-1", None),   # 등록되지 않은 제공자
            IdentityRevocation(Provider.APPLE, "apple-1", "secret-refresh-token"),
        ])
    assert apple.revoked == ["apple-1"]
    assert "kakao" in caplog.text and "google" in caplog.text
    assert "secret-refresh-token" not in caplog.text


async def test_예상하지_못한_예외가_나도_나머지는_끊고_예외_메시지를_로그에_남기지_않는다(caplog):
    kakao = _StubProvider(unexpected_error=RuntimeError("Bearer secret-refresh-token leaked in message"))
    apple = _StubProvider()
    revoker = ProviderRevoker(_StubResolver({Provider.KAKAO: kakao, Provider.APPLE: apple}))
    with caplog.at_level(logging.WARNING):
        await revoker.revoke_all([
            IdentityRevocation(Provider.KAKAO, "kakao-1", None),
            IdentityRevocation(Provider.APPLE, "apple-1", "secret-refresh-token"),
        ])
    assert apple.revoked == ["apple-1"]
    assert "RuntimeError" in caplog.text and "kakao" in caplog.text
    assert "secret-refresh-token" not in caplog.text
