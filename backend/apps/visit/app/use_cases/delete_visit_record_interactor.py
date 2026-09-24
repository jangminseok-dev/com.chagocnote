from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.errors import RecordNotFoundError


class DeleteVisitRecordInteractor(DeleteVisitRecordUseCase):
    """기록을 지운다 — 방문은 남는다. 붙은 미디어는 놓고, 정리 스크립트가 지운다(설계 8절).
    상태와 상관없이 지울 수 있다(되돌린 방문에 남은 기록도)."""

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort,
    ) -> None:
        self._visits = visits
        self._records = records
        self._directory = directory
        self._library = library

    async def delete_visit_record(self, command: DeleteVisitRecordCommand) -> None:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        current = await self._records.get(ctx, visit.id)
        if current is None:
            raise RecordNotFoundError("기록이 없습니다.")
        await self._library.release(ctx, [m.media_id for m in current.media])
        await self._records.delete(ctx, visit.id)
