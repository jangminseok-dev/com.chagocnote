from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery, VisitFeedView


class ListVisitFeedUseCase(ABC):
    @abstractmethod
    async def list_visit_feed(self, query: ListVisitFeedQuery) -> VisitFeedView: ...
