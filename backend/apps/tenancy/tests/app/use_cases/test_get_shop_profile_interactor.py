from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from tenancy.app.use_cases.get_shop_profile_interactor import GetShopProfileInteractor
from tenancy.domain.entities.shop import Shop

WHEN = datetime(2026, 9, 28, 3, 0, tzinfo=timezone.utc)


class _StubShops:
    def __init__(self, shop):
        self.shop = shop
        self.calls = []

    async def find_by_id(self, shop_id):
        self.calls.append(shop_id)
        return self.shop


def _shop(**overrides):
    base = dict(id=3, name="Hiss Haus", business_type="pet_grooming", phone="02-000-0000", address="서울",
                timezone="Asia/Tokyo", suspended_at=None, closed_at=None)
    return Shop(**{**base, **overrides})


async def test_매장의_공개_정보를_돌려준다():
    shops = _StubShops(_shop())
    profile = await GetShopProfileInteractor(shops).public_profile(3)
    assert profile == ShopProfile(shop_id=3, name="Hiss Haus", phone="02-000-0000", address="서울",
                                  timezone="Asia/Tokyo", open=True)
    assert shops.calls == [3]


async def test_없는_매장이면_None_이다():
    assert await GetShopProfileInteractor(_StubShops(None)).public_profile(3) is None


@pytest.mark.parametrize("stopped", [
    {"suspended_at": WHEN}, {"closed_at": WHEN}, {"suspended_at": WHEN, "closed_at": WHEN},
], ids=["suspended_at", "closed_at", "both"])
async def test_정지했거나_폐업한_매장은_영업_중이_아니다(stopped):
    profile = await GetShopProfileInteractor(_StubShops(_shop(**stopped))).public_profile(3)
    assert (profile.name, profile.open) == ("Hiss Haus", False)


async def test_전화와_주소가_비면_None_이다():
    profile = await GetShopProfileInteractor(_StubShops(_shop(phone=None, address=None))).public_profile(3)
    assert (profile.phone, profile.address) == (None, None)
