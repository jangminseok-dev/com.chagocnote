from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_due_pets_dto import DuePetsView, ListDuePetsQuery


class ListDuePetsUseCase(ABC):
    @abstractmethod
    async def list_due_pets(self, query: ListDuePetsQuery) -> DuePetsView: ...
