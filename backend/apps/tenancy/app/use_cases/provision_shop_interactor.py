from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from hub.app.dtos.provisioned_shop import ProvisionedShop
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.services.invite_code import INVITE_TTL, generate_invite_code, hash_invite_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProvisionShopInteractor(ShopProvisioningPort):
    """허브의 ShopProvisioningPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(
        self, shops: ShopRepository, invites: InviteRepository,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._shops = shops
        self._invites = invites
        self._now = now

    async def create_shop(self, name: str, business_type: str) -> ProvisionedShop:
        shop = await self._shops.create(name, business_type)
        code = generate_invite_code()
        expires_at = self._now() + INVITE_TTL
        await self._invites.create_owner_invite(shop.id, hash_invite_code(code), expires_at)
        return ProvisionedShop(
            shop_id=shop.id, name=shop.name, owner_invite_code=code, invite_expires_at=expires_at
        )
