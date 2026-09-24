from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_menu
from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.menu import Menu
from visit.domain.errors import MenuNameTakenError, MenuNotFoundError

_NAME_UNIQUE = "uq_service_menus_shop_name_active"


class MenuPgRepository(MenuRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, ctx: ShopContext, include_archived: bool) -> list[Menu]:
        stmt = select(ServiceMenuOrm).where(ServiceMenuOrm.shop_id == ctx.shop_id)
        if not include_archived:
            stmt = stmt.where(ServiceMenuOrm.archived_at.is_(None))
        rows = (
            await self._session.execute(
                stmt.order_by(ServiceMenuOrm.sort_order, ServiceMenuOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
        return [to_menu(row) for row in rows]

    async def list_active_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
        rows = (
            await self._session.execute(
                select(ServiceMenuOrm).where(
                    ServiceMenuOrm.id.in_(menu_ids), ServiceMenuOrm.shop_id == ctx.shop_id,
                    ServiceMenuOrm.archived_at.is_(None),
                )
            )
        ).scalars()
        return [to_menu(row) for row in rows]

    async def list_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
        rows = (
            await self._session.execute(
                select(ServiceMenuOrm).where(ServiceMenuOrm.id.in_(menu_ids), ServiceMenuOrm.shop_id == ctx.shop_id)
            )
        ).scalars()
        return [to_menu(row) for row in rows]

    async def create(
        self, ctx: ShopContext, name: str, default_duration_minutes: int | None, price: int | None
    ) -> Menu:
        next_order = (
            select(func.least(func.coalesce(func.max(ServiceMenuOrm.sort_order), 0) + 1, 32_767))
            .where(ServiceMenuOrm.shop_id == ctx.shop_id)
            .scalar_subquery()
        )
        async with self._name_guard():
            menu_id = (
                await self._session.execute(
                    insert(ServiceMenuOrm)
                    .values(shop_id=ctx.shop_id, name=name,
                            default_duration_minutes=default_duration_minutes, sort_order=next_order, price=price)
                    .returning(ServiceMenuOrm.id)
                )
            ).scalar_one()
        return await self._get(ctx, menu_id)

    async def update(
        self, ctx: ShopContext, menu_id: int, name: str, default_duration_minutes: int | None,
        sort_order: int, price: int | None,
    ) -> Menu:
        async with self._name_guard():
            await self._session.execute(
                update(ServiceMenuOrm)
                .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
                .values(name=name, default_duration_minutes=default_duration_minutes, sort_order=sort_order,
                        price=price)
            )
        return await self._get(ctx, menu_id)

    async def archive(self, ctx: ShopContext, menu_id: int) -> Menu:
        await self._session.execute(
            update(ServiceMenuOrm)
            .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
            .values(archived_at=func.coalesce(ServiceMenuOrm.archived_at, func.now()))
        )
        return await self._get(ctx, menu_id)

    async def _get(self, ctx: ShopContext, menu_id: int) -> Menu:
        row = (
            await self._session.execute(
                select(ServiceMenuOrm)
                .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise MenuNotFoundError("메뉴를 찾을 수 없습니다.")
        return to_menu(row)

    @asynccontextmanager
    async def _name_guard(self):
        """이름 유일 색인 위반을 MENU_NAME_TAKEN 으로 바꾼다. 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""
        try:
            async with self._session.begin_nested():
                yield
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) == _NAME_UNIQUE:
                raise MenuNameTakenError("같은 이름의 메뉴가 있습니다.") from exc
            raise
