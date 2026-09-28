from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.mappers.tenancy_mapper import to_shop
from tenancy.adapter.outbound.orm.tenancy_orm import ShopOrm
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.entities.shop import Shop


class ShopPgRepository(ShopRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, business_type: str) -> Shop:
        row = ShopOrm(name=name, business_type=business_type)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)  # 서버 기본값(timezone 등)을 읽어 온다
        return to_shop(row)

    async def get_by_id(self, shop_id: int) -> Shop:
        return to_shop(await self._row(shop_id))

    async def find_by_id(self, shop_id: int) -> Shop | None:
        row = await self._session.get(ShopOrm, shop_id)
        return to_shop(row) if row is not None else None

    async def get(self, ctx: ShopContext) -> Shop:
        return to_shop(await self._row(ctx.shop_id))

    async def update(
        self, ctx: ShopContext, name: str, phone: str | None, address: str | None
    ) -> Shop:
        row = await self._row(ctx.shop_id)
        row.name, row.phone, row.address = name, phone, address
        await self._session.flush()
        return to_shop(row)

    async def close(self, ctx: ShopContext) -> None:
        await self._session.execute(
            update(ShopOrm).where(ShopOrm.id == ctx.shop_id).values(closed_at=func.now())
        )

    async def _row(self, shop_id: int) -> ShopOrm:
        return (
            await self._session.execute(select(ShopOrm).where(ShopOrm.id == shop_id))
        ).scalar_one()
