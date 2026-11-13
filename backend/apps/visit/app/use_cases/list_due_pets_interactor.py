from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.list_due_pets_dto import DuePetItemView, DuePetsView, ListDuePetsQuery
from visit.app.ports.input.list_due_pets_use_case import ListDuePetsUseCase
from visit.app.ports.output.sales_repository import SalesRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.due_pets import due_pets
from visit.app.services.pet_cards import pet_cards
from visit.domain.services.sales_cursor import decode_due_cursor, encode_due_cursor

PAGE_SIZE = 20


class ListDuePetsInteractor(ListDuePetsUseCase):
    """다시 올 때가 지난 아이(설계 ⑧ 3.3) — 마지막 방문이 오래된 순. 후보는 지난 한 해에 온 아이로 묶여 있어
    다 읽고 거른 뒤 여기서 쪽을 나눈다. 요약의 수와 같은 거르기(`due_pets`)를 쓴다."""

    def __init__(
        self, sales: SalesRepository, directory: CustomerDirectoryPort, records: VisitRecordRepository,
        library: MediaLibraryPort, now: Callable[[], datetime],
    ) -> None:
        self._sales = sales
        self._directory = directory
        self._records = records
        self._library = library
        self._now = now

    async def list_due_pets(self, query: ListDuePetsQuery) -> DuePetsView:
        ctx = query.ctx
        after = decode_due_cursor(query.cursor) if query.cursor else None
        now = self._now()
        due, pets = await due_pets(
            ctx, self._sales, self._directory, now.astimezone(ZoneInfo(ctx.timezone)).date(), now)
        if after is not None:
            due = [d for d in due if (d.last_day, d.pet_id) > after]
        page = due[:PAGE_SIZE]
        cards = await pet_cards(ctx, pets, [d.pet_id for d in page], self._records, self._library)
        return DuePetsView(
            items=[DuePetItemView(pet=cards[d.pet_id], last_visit_date=d.last_day) for d in page],
            next_cursor=encode_due_cursor(page[-1].last_day, page[-1].pet_id) if len(due) > PAGE_SIZE else None,
        )
