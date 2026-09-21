from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.provisioned_shop import ProvisionedShop


class ShopProvisioningPort(ABC):
    """구현: tenancy. 사용: platform_admin."""

    @abstractmethod
    async def create_shop(self, name: str, business_type: str) -> ProvisionedShop:
        """매장을 만들고 사장용 초대 코드를 발급한다."""
