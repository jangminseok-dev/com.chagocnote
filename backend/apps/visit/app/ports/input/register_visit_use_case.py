from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.register_visit_dto import RegisteredVisitsView, RegisterVisitCommand


class RegisterVisitUseCase(ABC):
    @abstractmethod
    async def register_visit(self, command: RegisterVisitCommand) -> RegisteredVisitsView: ...
