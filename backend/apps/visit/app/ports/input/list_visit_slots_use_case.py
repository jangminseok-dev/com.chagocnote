from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery, VisitSlotsView


class ListVisitSlotsUseCase(ABC):
    @abstractmethod
    async def list_visit_slots(self, query: ListVisitSlotsQuery) -> VisitSlotsView: ...
