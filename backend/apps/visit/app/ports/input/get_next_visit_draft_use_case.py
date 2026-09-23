from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, NextVisitDraftView


class GetNextVisitDraftUseCase(ABC):
    @abstractmethod
    async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView: ...
