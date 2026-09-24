from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand


class DeleteVisitRecordUseCase(ABC):
    @abstractmethod
    async def delete_visit_record(self, command: DeleteVisitRecordCommand) -> None: ...
