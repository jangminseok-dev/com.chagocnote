from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.guardian_report_dto import (
    GuardianReportItemView,
    GuardianReportPageView,
    ListGuardianReportsQuery,
)
from visit.app.dtos.report_view_dto import ReportCoverView
from visit.app.ports.input.list_guardian_reports_use_case import ListGuardianReportsUseCase
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.guardian_scope import guardian_scope
from visit.domain.services.guardian_cursor import decode_cursor, encode_cursor
from visit.domain.services.report_rules import report_cover_media_id, visible_media
from visit.domain.services.visit_schedule import local_date

PAGE_SIZE = 20


class ListGuardianReportsInteractor(ListGuardianReportsUseCase):
    """보호자가 받은 지난 알림장, 최신순 20개씩. 기간이 지난 것도 있고 매장이 끊은 것은 없다.
    대표 사진과 수는 매장이 뺀 것을 제외한 것이다. 읽기만 하므로 잠그지 않는다."""

    def __init__(
        self, reports: GuardianReportRepository, records: VisitRecordRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort, shops: ShopProfilePort,
    ) -> None:
        self._reports = reports
        self._records = records
        self._directory = directory
        self._library = library
        self._shops = shops

    async def list_reports(self, query: ListGuardianReportsQuery) -> GuardianReportPageView:
        before = decode_cursor(query.cursor) if query.cursor is not None else None
        scope = await guardian_scope(query.guardian, self._shops)
        if scope is None:
            return GuardianReportPageView(items=(), next_cursor=None)
        ctx, _ = scope
        found = await self._reports.list_sent(
            ctx, query.guardian.customer_id, pet_id=query.pet_id, before=before, limit=PAGE_SIZE + 1)
        page, more = found[:PAGE_SIZE], len(found) > PAGE_SIZE
        records = await self._records.list_many(ctx, [s.visit.id for s in page])
        covers = {s.visit.id: report_cover_media_id(records[s.visit.id]) for s in page if s.visit.id in records}
        urls = await self._library.read_urls(ctx, [m for m in covers.values() if m is not None])
        pet_ids = sorted({s.visit.pet_id for s in page if s.visit.pet_id is not None})
        pets = (await self._directory.briefs(ctx, [], pet_ids)).pets if pet_ids else {}
        items = []
        for sent in page:
            record = records.get(sent.visit.id)
            if record is None:
                continue
            cover = urls.get(covers[sent.visit.id])
            pet = pets.get(sent.visit.pet_id)
            items.append(GuardianReportItemView(
                report_id=sent.report.id, visit_date=local_date(sent.visit.starts_at, ctx.timezone),
                pet_id=sent.visit.pet_id, pet_name=pet.name if pet is not None else None,
                cover=ReportCoverView(url=cover.thumb_url, width=cover.width, height=cover.height)
                if cover is not None else None,
                media_count=len(visible_media(record)),
            ))
        last = page[-1].visit if page else None
        return GuardianReportPageView(
            items=tuple(items),
            next_cursor=encode_cursor(last.starts_at, last.id) if more and last is not None else None,
        )
