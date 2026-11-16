from __future__ import annotations

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.form_settings_orm import ShopConsentTextOrm
from customer.app.ports.output.consent_text_repository import ConsentTextRepository
from hub.app.dtos.shop_context import ShopContext


class ConsentTextPgRepository(ConsentTextRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(self, ctx: ShopContext) -> dict[str, tuple[int, str | None]]:
        newest = (
            select(ShopConsentTextOrm.part, func.max(ShopConsentTextOrm.version).label("version"))
            .where(ShopConsentTextOrm.shop_id == ctx.shop_id).group_by(ShopConsentTextOrm.part).subquery()
        )
        rows = (
            await self._session.execute(
                select(ShopConsentTextOrm.part, ShopConsentTextOrm.version, ShopConsentTextOrm.body)
                .join(newest, (ShopConsentTextOrm.part == newest.c.part)
                      & (ShopConsentTextOrm.version == newest.c.version))
                .where(ShopConsentTextOrm.shop_id == ctx.shop_id)
            )
        ).all()
        return {row.part: (row.version, row.body) for row in rows}

    async def body_of(self, ctx: ShopContext, part: str, version: int) -> str | None:
        return (
            await self._session.execute(
                select(ShopConsentTextOrm.body).where(
                    ShopConsentTextOrm.shop_id == ctx.shop_id, ShopConsentTextOrm.part == part,
                    ShopConsentTextOrm.version == version,
                )
            )
        ).scalar_one_or_none()

    async def append(self, ctx: ShopContext, part: str, body: str | None) -> int:
        last = (
            await self._session.execute(
                select(func.max(ShopConsentTextOrm.version)).where(
                    ShopConsentTextOrm.shop_id == ctx.shop_id, ShopConsentTextOrm.part == part)
            )
        ).scalar_one()
        version = (last or 0) + 1
        await self._session.execute(insert(ShopConsentTextOrm).values(
            shop_id=ctx.shop_id, part=part, version=version, body=body, created_by_member_id=ctx.member_id))
        return version
