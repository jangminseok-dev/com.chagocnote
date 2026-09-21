from __future__ import annotations

from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand
from tenancy.app.ports.input.update_shop_use_case import UpdateShopUseCase
from tenancy.app.ports.output.shop_repository import ShopRepository


class UpdateShopInteractor(UpdateShopUseCase):
    def __init__(self, shops: ShopRepository) -> None:
        self._shops = shops

    async def update_shop(self, command: UpdateShopCommand) -> ShopView:
        shop = await self._shops.update(command.ctx, command.name, command.phone, command.address)
        return ShopView.of(shop)
