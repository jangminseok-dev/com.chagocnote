from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.parse_visit_draft_dto import ParseVisitDraftCommand, VisitDraftView


class ParseVisitDraftUseCase(ABC):
    @abstractmethod
    async def parse_visit_draft(self, command: ParseVisitDraftCommand) -> VisitDraftView: ...
