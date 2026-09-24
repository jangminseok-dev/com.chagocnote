from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.dtos.record_view_dto import RecordView


class PutVisitRecordUseCase(ABC):
    @abstractmethod
    async def put_visit_record(self, command: PutVisitRecordCommand) -> RecordView: ...
