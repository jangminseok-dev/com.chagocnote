from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.menu_view_dto import MenuView
from visit.app.dtos.update_menu_dto import UpdateMenuCommand


class UpdateMenuUseCase(ABC):
    @abstractmethod
    async def update_menu(self, command: UpdateMenuCommand) -> MenuView: ...
