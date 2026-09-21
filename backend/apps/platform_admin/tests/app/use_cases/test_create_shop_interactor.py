from datetime import datetime, timezone

from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.use_cases.create_shop_interactor import CreateShopInteractor

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubProvisioning:
    def __init__(self):
        self.calls = []

    async def create_shop(self, name, business_type):
        self.calls.append((name, business_type))
        return ProvisionedShop(shop_id=3, name=name, owner_invite_code="ABCD2345", invite_expires_at=EXPIRES)


async def test_매장을_개설하고_사장용_초대_코드를_돌려준다():
    """운영자 확인은 라우터의 require_operator 가드가 한다. 여기서 다시 하지 않는다."""
    provisioning = _StubProvisioning()
    result = await CreateShopInteractor(provisioning).create_shop(
        CreateShopCommand(name="Hiss Haus", business_type="pet_grooming")
    )
    assert provisioning.calls == [("Hiss Haus", "pet_grooming")]
    assert (result.shop_id, result.owner_invite_code) == (3, "ABCD2345")
