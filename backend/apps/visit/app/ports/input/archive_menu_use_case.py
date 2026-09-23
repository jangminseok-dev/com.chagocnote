from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.dtos.menu_view_dto import MenuView


class ArchiveMenuUseCase(ABC):
    @abstractmethod
    async def archive_menu(self, command: ArchiveMenuCommand) -> MenuView: ...
