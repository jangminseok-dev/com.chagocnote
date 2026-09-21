from datetime import datetime, timedelta, timezone

from tenancy.app.use_cases.provision_shop_interactor import ProvisionShopInteractor
from tenancy.domain.entities.shop import Shop
from tenancy.domain.services.invite_code import hash_invite_code

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class _StubShops:
    def __init__(self):
        self.created = []

    async def create(self, name, business_type):
        self.created.append((name, business_type))
        return Shop(id=3, name=name, business_type=business_type, phone=None, address=None,
                    timezone="Asia/Seoul", suspended_at=None, closed_at=None)


class _StubInvites:
    def __init__(self):
        self.owner_invites = []

    async def create_owner_invite(self, shop_id, code_hash, expires_at):
        self.owner_invites.append((shop_id, code_hash, expires_at))


async def test_매장을_만들고_사장용_초대_코드를_돌려준다():
    shops, invites = _StubShops(), _StubInvites()
    result = await ProvisionShopInteractor(shops, invites, now=lambda: NOW).create_shop(
        "Hiss Haus", "pet_grooming"
    )
    assert shops.created == [("Hiss Haus", "pet_grooming")]
    assert (result.shop_id, result.name) == (3, "Hiss Haus")
    assert len(result.owner_invite_code) == 8
    assert result.invite_expires_at == NOW + timedelta(days=7)


async def test_초대는_해시로만_저장한다():
    invites = _StubInvites()
    result = await ProvisionShopInteractor(_StubShops(), invites, now=lambda: NOW).create_shop(
        "Hiss Haus", "pet_grooming"
    )
    shop_id, code_hash, expires_at = invites.owner_invites[0]
    assert shop_id == 3
    assert code_hash == hash_invite_code(result.owner_invite_code)
    assert result.owner_invite_code not in code_hash
    assert expires_at == result.invite_expires_at
