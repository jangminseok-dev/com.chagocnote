import httpx
import pytest

from auth.adapter.outbound.factory.social_provider_factory import (
    AppleSettings,
    build_social_provider_factory,
)
from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.domain.errors import UnsupportedProviderError
from auth.domain.value_objects.provider import Provider
from auth.tests.helpers.keys import make_ec_private_pem


def _build(**overrides):
    base = dict(app_env="dev", kakao_app_id="", google_client_ids=(), apple=None,
                http=httpx.AsyncClient())
    return build_social_provider_factory(**{**base, **overrides})


def test_개발_환경에서는_dev_제공자가_등록된다():
    assert isinstance(_build(app_env="dev").resolve(Provider.DEV), DevIdentityStrategy)


def test_운영_환경에서는_dev_제공자가_등록되지_않는다():
    with pytest.raises(UnsupportedProviderError):
        _build(app_env="prod").resolve(Provider.DEV)


def test_설정값이_있는_제공자만_등록된다():
    factory = _build(kakao_app_id="1234")
    assert isinstance(factory.resolve(Provider.KAKAO), KakaoIdentityStrategy)
    with pytest.raises(UnsupportedProviderError):
        factory.resolve(Provider.GOOGLE)
    with pytest.raises(UnsupportedProviderError):
        factory.resolve(Provider.APPLE)


def test_Apple_설정이_모두_있으면_Apple_제공자가_등록된다():
    apple = AppleSettings("com.chagocnote.app", "TEAM123456", "KEY1234567", make_ec_private_pem())
    assert _build(apple=apple).resolve(Provider.APPLE) is not None
