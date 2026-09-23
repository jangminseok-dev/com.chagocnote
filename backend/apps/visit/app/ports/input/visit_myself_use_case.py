from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.visit_myself_dto import VisitMyselfQuery, VisitMyselfResponse


class VisitMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: VisitMyselfQuery) -> VisitMyselfResponse: ...
