from __future__ import annotations

from visit.app.dtos.menu_view_dto import MenuView
from visit.app.dtos.update_menu_dto import UpdateMenuCommand
from visit.app.ports.input.update_menu_use_case import UpdateMenuUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.services.visit_schedule import check_duration


class UpdateMenuInteractor(UpdateMenuUseCase):
    """이름·기본 소요·순서를 바꾼다. 이미 잡힌 예약의 소요는 그대로다(방문이 자기 소요를 가진다)."""

    def __init__(self, menus: MenuRepository) -> None:
        self._menus = menus

    async def update_menu(self, command: UpdateMenuCommand) -> MenuView:
        if command.default_duration_minutes is not None:
            check_duration(command.default_duration_minutes)
        menu = await self._menus.update(
            command.ctx, command.menu_id, command.name, command.default_duration_minutes,
            command.sort_order,
        )
        return MenuView.of(menu)
