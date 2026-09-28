from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.list_visit_feed_dto import FeedItemView, ListVisitFeedQuery, VisitFeedView
from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.cover_reader import cover_urls
from visit.app.services.visit_reader import describe_visits

CARE_NOTE_PREVIEW = 80


class ListVisitFeedInteractor(ListVisitFeedUseCase):
    """피드 — 완료 방문을 완료 시각 역순으로 이어 읽는다(설계 9절). 한 쪽을 읽는 데 질의 수가 방문 수와 상관없다."""

    def __init__(
        self, feed: VisitFeedRepository, records: VisitRecordRepository, menus: MenuRepository,
        reports: ReportRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._feed = feed
        self._records = records
        self._menus = menus
        self._reports = reports
        self._directory = directory
        self._library = library
        self._now = now

    async def list_visit_feed(self, query: ListVisitFeedQuery) -> VisitFeedView:
        ctx = query.ctx
        page = await self._feed.list_completed(ctx, query.cursor, query.limit, query.pet_id)
        views = await describe_visits(ctx, page.visits, self._directory, self._menus)
        records = await self._records.list_many(ctx, [v.id for v in page.visits])
        covers = await cover_urls(ctx, records, self._library)
        sent = await self._reports.live_visit_ids(ctx, [v.id for v in page.visits], self._now())
        item_ids = sorted({i.menu_id for r in records.values() for i in r.items})
        names = {m.id: m.name for m in await self._menus.list_by_ids(ctx, item_ids)} if item_ids else {}
        zone = ZoneInfo(ctx.timezone)
        items = []
        for visit, view in zip(page.visits, views):
            record = records.get(visit.id)
            actual = [names[i.menu_id] for i in record.items] if record else []
            note = record.care_note if record else None
            items.append(FeedItemView(
                visit_id=visit.id, customer=view.customer, pet=view.pet,
                completed_at=visit.completed_at.astimezone(zone), cover=covers.get(visit.id),
                menus=actual or [m.name for m in view.menus],
                care_note=note[:CARE_NOTE_PREVIEW] if note else None,
                media_count=len(record.media) if record else 0,
                report_sent=visit.id in sent,
            ))
        return VisitFeedView(items=items, next_cursor=page.next_cursor)
