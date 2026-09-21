from datetime import datetime, timezone

import pytest

from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.use_cases.create_shop_interactor import CreateShopInteractor
from platform_admin.domain.errors import NotAnOperatorError

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def is_operator(self, user_id):
        return user_id in self.operator_ids


class _StubProvisioning:
    def __init__(self):
        self.calls = []

    async def create_shop(self, name, business_type):
        self.calls.append((name, business_type))
        return ProvisionedShop(shop_id=3, name=name, owner_invite_code="ABCD2345", invite_expires_at=EXPIRES)


async def test_운영자는_매장을_개설한다():
    provisioning = _StubProvisioning()
    result = await CreateShopInteractor(_StubOperators([5]), provisioning).create_shop(
        CreateShopCommand(user_id=5, name="Hiss Haus", business_type="pet_grooming")
    )
    assert provisioning.calls == [("Hiss Haus", "pet_grooming")]
    assert (result.shop_id, result.owner_invite_code) == (3, "ABCD2345")


async def test_운영자가_아니면_개설하지_않는다():
    provisioning = _StubProvisioning()
    with pytest.raises(NotAnOperatorError):
        await CreateShopInteractor(_StubOperators([5]), provisioning).create_shop(
            CreateShopCommand(user_id=6, name="Hiss Haus", business_type="pet_grooming")
        )
    assert provisioning.calls == []
