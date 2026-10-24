from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand


class HandleVisitEventUseCase(ABC):
    @abstractmethod
    async def handle_visit_event(self, command: HandleVisitEventCommand) -> None: ...
