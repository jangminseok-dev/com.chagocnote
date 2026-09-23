from __future__ import annotations

from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.dtos.menu_view_dto import MenuView
from visit.app.ports.input.create_menu_use_case import CreateMenuUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.visit_schedule import check_duration


class CreateMenuInteractor(CreateMenuUseCase):
    def __init__(self, schedule: ScheduleRepository, menus: MenuRepository) -> None:
        self._schedule = schedule
        self._menus = menus

    async def create_menu(self, command: CreateMenuCommand) -> MenuView:
        if command.default_duration_minutes is not None:
            check_duration(command.default_duration_minutes)
        await self._schedule.ensure(command.ctx)   # 메뉴는 설정 행을 가리킨다(외래 키)
        return MenuView.of(
            await self._menus.create(command.ctx, command.name, command.default_duration_minutes)
        )
