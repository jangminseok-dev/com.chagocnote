"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
from __future__ import annotations

from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeSchedule:
    def __init__(self, journal: Journal | None = None, settings=DEFAULT_SETTINGS) -> None:
        self.journal = journal if journal is not None else Journal()
        self.settings = settings
        self.closed: dict[tuple[int, object], ClosedDate] = {}

    async def ensure(self, ctx):
        self.journal.append(("ensure", ctx.shop_id))
        return self.settings

    async def update(self, ctx, settings):
        self.journal.append(("update_settings", ctx.shop_id))
        self.settings = settings
        return settings

    async def list_closed_dates(self, ctx, start, end):
        return sorted(
            (c for (shop, day), c in self.closed.items() if shop == ctx.shop_id and start <= day <= end),
            key=lambda c: c.day,
        )

    async def add_closed_date(self, ctx, day, note):
        self.journal.append(("add_closed_date", day))
        return self.closed.setdefault((ctx.shop_id, day), ClosedDate(day=day, note=note))

    async def delete_closed_date(self, ctx, day):
        self.journal.append(("delete_closed_date", day))
        self.closed.pop((ctx.shop_id, day), None)
