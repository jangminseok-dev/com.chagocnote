import pytest

from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


async def test_입력한_이름이_곧_신원이다():
    profile = await DevIdentityStrategy().verify(SocialCredentials(token=" Owner "))
    assert profile.provider is Provider.DEV
    assert profile.provider_user_id == "owner"
    assert profile.display_name == "Owner"


async def test_이름이_비어_있으면_거절한다():
    with pytest.raises(ProviderVerificationError):
        await DevIdentityStrategy().verify(SocialCredentials(token="   "))
