from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand


class DeleteClosedDateUseCase(ABC):
    @abstractmethod
    async def delete_closed_date(self, command: DeleteClosedDateCommand) -> None: ...
