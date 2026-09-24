from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.dtos.record_view_dto import RecordView
from visit.app.ports.input.append_record_media_use_case import AppendRecordMediaUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.record_reader import describe_record
from visit.app.services.visit_locking import lock_visits
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.services.visit_record_rules import (
    append_media,
    check_media_limits,
    check_recordable,
    next_version,
)


class AppendRecordMediaInteractor(AppendRecordMediaUseCase):
    """사진·영상 하나를 덧붙인다(설계 8절). 기록이 없으면 빈 기록을 만든다. 버전은 받지 않고 올린다.

    같은 미디어가 이미 이 기록에 있으면 아무것도 바꾸지 않는다 — 대기열이 응답을 못 받고 다시 보내도 안전하다.
    잠금·상태 규칙은 전체 교체와 같다(고객 행 → 방문 행, 미용 중·완료만).
    """

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, menus: MenuRepository,
        directory: CustomerDirectoryPort, library: MediaLibraryPort,
    ) -> None:
        self._visits = visits
        self._records = records
        self._menus = menus
        self._directory = directory
        self._library = library

    async def append_record_media(self, command: AppendRecordMediaCommand) -> RecordView:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        check_recordable(visit)
        current = await self._records.get(ctx, visit.id)
        if current is not None and any(m.media_id == command.media_id for m in current.media):
            return await describe_record(ctx, current, self._menus, self._library)
        kinds = await self._library.claim(ctx, [command.media_id])
        media = append_media(current.media if current else (), command.media_id, kinds[command.media_id],
                             command.phase)
        check_media_limits(m.kind for m in media)
        saved = await self._records.save(ctx, VisitRecord(
            visit_id=visit.id,
            weight_kg=current.weight_kg if current else None,
            care_note=current.care_note if current else None,
            internal_note=current.internal_note if current else None,
            payment_method=current.payment_method if current else None,
            total_amount=current.total_amount if current else None,
            items=current.items if current else (),
            media=media,
            version=next_version(current),
            created_by_member_id=current.created_by_member_id if current else ctx.member_id,
            updated_by_member_id=ctx.member_id,
        ))
        return await describe_record(ctx, saved, self._menus, self._library)
