from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.list_sales_visits_dto import ListSalesVisitsQuery, SalesVisitItemView, SalesVisitsView
from visit.app.ports.input.list_sales_visits_use_case import ListSalesVisitsUseCase
from visit.app.ports.output.sales_repository import SalesRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.pet_cards import pet_cards, showable_pets
from visit.domain.errors import VisitInputError
from visit.domain.services.sales_cursor import decode_visit_cursor, encode_visit_cursor
from visit.domain.services.sales_period import check_anchor, period_of

PAGE_SIZE = 20


class ListSalesVisitsInteractor(ListSalesVisitsUseCase):
    """매출 탭의 숫자를 누르면 나오는 방문들 — 금액을 적지 않은 완료 방문, 노쇼, 취소, 어떤 메뉴를 한 방문.
    그 기간의 것만, 최신순으로 이어 읽는다."""

    def __init__(
        self, sales: SalesRepository, directory: CustomerDirectoryPort, records: VisitRecordRepository,
        library: MediaLibraryPort, now: Callable[[], datetime],
    ) -> None:
        self._sales = sales
        self._directory = directory
        self._records = records
        self._library = library
        self._now = now

    async def list_sales_visits(self, query: ListSalesVisitsQuery) -> SalesVisitsView:
        ctx = query.ctx
        if query.filter == "menu" and query.menu_id is None:
            raise VisitInputError("어느 메뉴의 방문을 볼지 골라 주세요.")
        before = decode_visit_cursor(query.cursor) if query.cursor else None
        today = self._now().astimezone(ZoneInfo(ctx.timezone)).date()
        period = period_of(query.span, check_anchor(query.anchor) if query.anchor else today)

        rows = await self._sales.list_visits(
            ctx, period.start, period.until, query.filter,
            query.menu_id if query.filter == "menu" else None, before, PAGE_SIZE + 1,
        )
        page = rows[:PAGE_SIZE]
        pet_ids = [row.pet_id for row in page if row.pet_id is not None]
        cards = await pet_cards(
            ctx, await showable_pets(ctx, pet_ids, self._directory), pet_ids, self._records, self._library)
        last = page[-1] if len(rows) > PAGE_SIZE else None
        return SalesVisitsView(
            items=[
                SalesVisitItemView(visit_id=row.visit_id, date=row.day, pet=cards.get(row.pet_id), amount=row.amount)
                for row in page
            ],
            next_cursor=encode_visit_cursor(last.starts_at, last.visit_id) if last else None,
        )
