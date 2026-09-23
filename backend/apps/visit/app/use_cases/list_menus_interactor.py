from __future__ import annotations

from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.dtos.menu_view_dto import MenuView
from visit.app.ports.input.list_menus_use_case import ListMenusUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository


class ListMenusInteractor(ListMenusUseCase):
    """처음 여는 매장이면 기본 메뉴가 이때 생긴다 — 사장이 메뉴표를 만들지 않아도 바로 쓴다."""

    def __init__(self, schedule: ScheduleRepository, menus: MenuRepository) -> None:
        self._schedule = schedule
        self._menus = menus

    async def list_menus(self, query: ListMenusQuery) -> list[MenuView]:
        await self._schedule.ensure(query.ctx)
        return [MenuView.of(m) for m in await self._menus.list(query.ctx, query.include_archived)]
