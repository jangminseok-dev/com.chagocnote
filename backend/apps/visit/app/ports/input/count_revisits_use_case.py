from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.count_revisits_dto import CountRevisitsQuery, RevisitCountsView


class CountRevisitsUseCase(ABC):
    @abstractmethod
    async def count_revisits(self, query: CountRevisitsQuery) -> RevisitCountsView: ...
