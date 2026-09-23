from __future__ import annotations

from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.dtos.menu_view_dto import MenuView
from visit.app.ports.input.archive_menu_use_case import ArchiveMenuUseCase
from visit.app.ports.output.menu_repository import MenuRepository


class ArchiveMenuInteractor(ArchiveMenuUseCase):
    """메뉴는 지우지 않고 보관한다 — 지난 방문이 가리키고 있다. 보관한 메뉴는 새 예약에 고를 수 없다."""

    def __init__(self, menus: MenuRepository) -> None:
        self._menus = menus

    async def archive_menu(self, command: ArchiveMenuCommand) -> MenuView:
        return MenuView.of(await self._menus.archive(command.ctx, command.menu_id))
