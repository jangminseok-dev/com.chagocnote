from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.dtos.menu_view_dto import MenuView


class ListMenusUseCase(ABC):
    @abstractmethod
    async def list_menus(self, query: ListMenusQuery) -> list[MenuView]: ...
