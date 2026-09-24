from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.dtos.record_view_dto import RecordView


class AppendRecordMediaUseCase(ABC):
    @abstractmethod
    async def append_record_media(self, command: AppendRecordMediaCommand) -> RecordView: ...
