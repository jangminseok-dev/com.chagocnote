from __future__ import annotations

from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.guardian_report_dto import GuardianMediaItemView, GuardianMediaPageView, ListGuardianMediaQuery
from visit.app.ports.input.list_guardian_media_use_case import ListGuardianMediaUseCase
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.services.guardian_scope import guardian_scope
from visit.domain.services.guardian_cursor import decode_media_cursor, encode_media_cursor
from visit.domain.services.visit_schedule import local_date

PAGE_SIZE = 60


class ListGuardianMediaInteractor(ListGuardianMediaUseCase):
    """보호자가 아이의 사진·영상을 날짜를 넘어 모아 본다(⑫ 설계 3.4) — 최신순 60개씩. 나오는 미디어는 보호자가 볼 수
    있는 알림장 한 장들에 나오는 것과 같다(통합 테스트가 같음을 본다). 받는 주소는 원본 그대로다(다시 인코딩하지 않는다)."""

    def __init__(self, reports: GuardianReportRepository, library: MediaLibraryPort, shops: ShopProfilePort) -> None:
        self._reports = reports
        self._library = library
        self._shops = shops

    async def list_media(self, query: ListGuardianMediaQuery) -> GuardianMediaPageView:
        before = decode_media_cursor(query.cursor) if query.cursor is not None else None
        scope = await guardian_scope(query.guardian, self._shops)
        if scope is None:
            return GuardianMediaPageView(items=(), next_cursor=None, years=())
        ctx, _ = scope
        customer_id = query.guardian.customer_id
        found = await self._reports.list_media(
            ctx, customer_id, pet_id=query.pet_id, year=query.year, phase=query.phase, before=before,
            limit=PAGE_SIZE + 1)
        page, more = found[:PAGE_SIZE], len(found) > PAGE_SIZE
        urls = await self._library.read_urls(ctx, [m.media_id for m in page])
        items = tuple(
            GuardianMediaItemView(
                report_id=m.report_id, visit_date=local_date(m.starts_at, ctx.timezone), kind=m.kind, phase=m.phase,
                width=urls[m.media_id].width, height=urls[m.media_id].height,
                duration_seconds=urls[m.media_id].duration_seconds,
                display_url=urls[m.media_id].display_url or urls[m.media_id].original_url,
                thumb_url=urls[m.media_id].thumb_url, download_url=urls[m.media_id].download_url,
            )
            for m in page if m.media_id in urls
        )
        last = page[-1] if page else None
        return GuardianMediaPageView(
            items=items,
            next_cursor=encode_media_cursor(last.starts_at, last.visit_id, last.phase, last.sort_order)
            if more and last is not None else None,
            years=tuple(await self._reports.media_years(ctx, customer_id, pet_id=query.pet_id)),
        )
