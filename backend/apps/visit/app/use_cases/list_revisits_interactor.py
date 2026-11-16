from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.list_revisits_dto import ListRevisitsQuery, RevisitItemView, RevisitsView
from visit.app.ports.input.list_revisits_use_case import ListRevisitsUseCase
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.pet_cards import pet_cards
from visit.app.services.revisit import revisit_board, weeks_since
from visit.domain.errors import VisitInputError
from visit.domain.services.revisit_rules import fill_message
from visit.domain.services.sales_cursor import decode_due_cursor, encode_due_cursor
from visit.domain.services.visit_schedule import local_date

PAGE_SIZE = 20
BUCKETS = ("soon", "due")


class ListRevisitsInteractor(ListRevisitsUseCase):
    """다시 올 때가 된 아이 — 곧·지남 한 묶음씩, 다음 올 때가 이른 순(⑬ 설계 3.3). 사장·직원 모두 본다(돈이 없다).
    줄마다 안내 글이 써진 채 온다(보호자 이름·번호는 넣지 않는다). 후보를 다 읽고 거른 뒤 여기서 쪽을 나눈다."""

    def __init__(
        self, history: VisitHistoryRepository, directory: CustomerDirectoryPort, records: VisitRecordRepository,
        library: MediaLibraryPort, settings: RevisitSettingsRepository, shops: ShopProfilePort,
        now: Callable[[], datetime],
    ) -> None:
        self._history = history
        self._directory = directory
        self._records = records
        self._library = library
        self._settings = settings
        self._shops = shops
        self._now = now

    async def list_revisits(self, query: ListRevisitsQuery) -> RevisitsView:
        ctx = query.ctx
        if query.bucket not in BUCKETS:
            raise VisitInputError("묶음은 soon 이나 due 여야 합니다.")
        after = decode_due_cursor(query.cursor) if query.cursor else None
        today = local_date(self._now(), ctx.timezone)
        settings = await self._settings.get(ctx)
        board = await revisit_board(ctx, self._history, self._directory, settings, today)
        rows = [r for r in board.rows if r.bucket == query.bucket]
        if after is not None:
            rows = [r for r in rows if (r.cycle.due_date, r.pet_id) > after]
        page = rows[:PAGE_SIZE]
        cards = await pet_cards(ctx, board.pets, [r.pet_id for r in page], self._records, self._library)
        profile = await self._shops.public_profile(ctx.shop_id) if page else None
        shop_name = profile.name if profile is not None else ""
        items = [
            RevisitItemView(
                pet=cards[r.pet_id], last_visit_date=r.cycle.last_visit_date, last_visit_id=r.last_visit_id,
                cycle_weeks=r.cycle.weeks, cycle_source=r.cycle.source,
                last_interval_weeks=r.cycle.last_interval_weeks, due_date=r.cycle.due_date,
                estimated=r.cycle.estimated, nudged_on=r.nudged_on,
                message=fill_message(settings.revisit_message, shop=shop_name, pet=cards[r.pet_id].name,
                                     weeks=weeks_since(r.cycle.last_visit_date, today)),
            )
            for r in page if r.pet_id in cards
        ]
        more = len(rows) > PAGE_SIZE
        return RevisitsView(
            items=items,
            next_cursor=encode_due_cursor(page[-1].cycle.due_date, page[-1].pet_id) if more else None,
        )
