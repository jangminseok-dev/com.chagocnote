from __future__ import annotations

from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.app.ports.input.get_shop_use_case import GetShopUseCase
from tenancy.app.ports.output.shop_repository import ShopRepository


class GetShopInteractor(GetShopUseCase):
    def __init__(self, shops: ShopRepository) -> None:
        self._shops = shops

    async def get_shop(self, query: GetShopQuery) -> ShopView:
        return ShopView.of(await self._shops.get(query.ctx))
