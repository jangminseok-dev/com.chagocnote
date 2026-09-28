from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.dtos.record_view_dto import RecordView
from visit.app.ports.input.put_visit_record_use_case import PutVisitRecordUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.completion_effects import sync_pet_weight
from visit.app.services.record_reader import describe_record
from visit.app.services.visit_locking import lock_visits
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import MenuNotAvailableError, RecordSalesForbiddenError
from visit.domain.services.report_rules import carry_hidden
from visit.domain.services.visit_record_rules import (
    check_input,
    check_media_limits,
    check_recordable,
    check_version,
    next_version,
)


class PutVisitRecordInteractor(PutVisitRecordUseCase):
    """기록 전체 교체(설계 8절). 고객 행 → 방문 행을 잠그고, 다시 읽은 방문·기록으로 판정한 뒤 쓴다.

    새로 든 미디어는 가져가고(claim), 빠진 미디어는 놓는다(release) — 놓인 미디어는 정리 스크립트가 지운다.
    둘 다 조건부 UPDATE 라 잠금 안에서 불러도 된다. 하나라도 안 되면 요청 전체가 되돌려진다.
    저장은 미디어 줄을 지우고 다시 넣으므로, 알림장에서 뺀 표시를 미디어 ID 로 이어 붙인다 — 빠뜨리면 뺀 사진이
    보호자에게 보인다.
    """

    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, records: VisitRecordRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort,
    ) -> None:
        self._visits = visits
        self._history = history
        self._records = records
        self._menus = menus
        self._directory = directory
        self._library = library

    async def put_visit_record(self, command: PutVisitRecordCommand) -> RecordView:
        ctx, wanted = command.ctx, command.record
        if wanted.has_money and "sales:write" not in ctx.permissions:
            raise RecordSalesForbiddenError("금액을 적을 권한이 없습니다.")
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        check_recordable(visit)
        check_input(visit, wanted)
        current = await self._records.get(ctx, visit.id)
        check_version(current, command.version)
        menu_ids = [item.menu_id for item in wanted.items]
        if menu_ids and len(await self._menus.list_by_ids(ctx, menu_ids)) != len(menu_ids):
            raise MenuNotAvailableError("메뉴를 찾을 수 없습니다.")

        had = {m.media_id: m.kind for m in current.media} if current else {}
        wanted_ids = [p.media_id for p in wanted.media]
        kinds = had | await self._library.claim(ctx, [i for i in wanted_ids if i not in had])
        check_media_limits(kinds[i] for i in wanted_ids)
        await self._library.release(ctx, [i for i in had if i not in wanted_ids])

        saved = await self._records.save(ctx, VisitRecord(
            visit_id=visit.id, weight_kg=wanted.weight_kg, care_note=wanted.care_note,
            internal_note=wanted.internal_note, payment_method=wanted.payment_method,
            total_amount=wanted.total_amount, items=wanted.items,
            media=carry_hidden(current.media if current else (), tuple(
                RecordMedia(media_id=p.media_id, kind=kinds[p.media_id], phase=p.phase, sort_order=p.sort_order)
                for p in wanted.media)),
            version=next_version(current),
            created_by_member_id=current.created_by_member_id if current else ctx.member_id,
            updated_by_member_id=ctx.member_id,
        ))
        # 몸무게를 적거나 바꿨을 때만 현재 몸무게가 된다 — 메모만 고친 저장이 반려동물 쪽에서 고친 값을 덮지 않게.
        if current is None or current.weight_kg != saved.weight_kg:
            await sync_pet_weight(ctx, visit, saved.weight_kg, self._history, self._directory)
        return await describe_record(ctx, saved, self._menus, self._library)
