from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand


class UpdateVisitUseCase(ABC):
    @abstractmethod
    async def update_visit(self, command: UpdateVisitCommand) -> UpdatedVisitView: ...
