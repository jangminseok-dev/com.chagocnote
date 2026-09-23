from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand


class RescheduleVisitsUseCase(ABC):
    @abstractmethod
    async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView: ...
