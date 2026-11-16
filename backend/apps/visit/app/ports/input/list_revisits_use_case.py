from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_revisits_dto import ListRevisitsQuery, RevisitsView


class ListRevisitsUseCase(ABC):
    @abstractmethod
    async def list_revisits(self, query: ListRevisitsQuery) -> RevisitsView: ...
