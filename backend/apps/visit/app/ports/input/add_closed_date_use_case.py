from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.dtos.schedule_view_dto import ClosedDateView


class AddClosedDateUseCase(ABC):
    @abstractmethod
    async def add_closed_date(self, command: AddClosedDateCommand) -> ClosedDateView: ...
