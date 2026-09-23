from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand


class TransitionVisitsUseCase(ABC):
    @abstractmethod
    async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView: ...
