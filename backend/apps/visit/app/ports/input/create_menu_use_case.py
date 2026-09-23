from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.dtos.menu_view_dto import MenuView


class CreateMenuUseCase(ABC):
    @abstractmethod
    async def create_menu(self, command: CreateMenuCommand) -> MenuView: ...
