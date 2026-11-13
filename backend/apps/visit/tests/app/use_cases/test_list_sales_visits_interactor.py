from datetime import date, timedelta

import pytest

from visit.app.dtos.list_sales_visits_dto import ListSalesVisitsQuery
from visit.app.services.pet_cards import PetCard
from visit.app.use_cases.list_sales_visits_interactor import PAGE_SIZE, ListSalesVisitsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.services.sales_cursor import decode_visit_cursor
from visit.domain.value_objects.sales import SalesVisitRow
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeRecords, FakeSalesRepository, FakeVisits

NOW = kst(11, 14, 15)
NOV = (date(2026, 11, 1), date(2026, 12, 1))


class _World:
    def __init__(self):
        self.sales, self.directory, self.visits, self.library = (
            FakeSalesRepository(), FakeDirectory(), FakeVisits(), FakeLibrary())
        self.records = FakeRecords(self.visits)
        self.directory.family(1, pets=(101, 102))
        self.interactor = ListSalesVisitsInteractor(
            sales=self.sales, directory=self.directory, records=self.records, library=self.library,
            now=lambda: NOW)

    def rows(self, count, pet_id=101, amount=None):
        """최신순으로 count 줄 — 하루에 하나씩 거슬러 올라간다."""
        self.sales.visit_rows = [
            SalesVisitRow(visit_id=1000 - i, starts_at=kst(11, 14, 11) - timedelta(days=i),
                          day=date(2026, 11, 14) - timedelta(days=i), pet_id=pet_id, customer_id=1, amount=amount)
            for i in range(count)
        ]

    async def list(self, filter="unrecorded", span="month", anchor=None, menu_id=None, cursor=None):
        return await self.interactor.list_sales_visits(ListSalesVisitsQuery(
            ctx=ctx(), span=span, anchor=anchor, filter=filter, menu_id=menu_id, cursor=cursor))


@pytest.mark.parametrize("kind", ["unrecorded", "no_show", "canceled"])
async def test_종류와_기간을_저장소에_그대로_넘기고_한_줄_더_읽는다(kind):
    w = _World()
    await w.list(kind, menu_id=7)
    assert w.sales.visit_args == (*NOV, kind, None, None, PAGE_SIZE + 1)      # menu 가 아니면 menu_id 는 버린다


async def test_메뉴로_거르면_menu_id_를_넘기고_없으면_422_다():
    w = _World()
    await w.list("menu", menu_id=7)
    assert w.sales.visit_args == (*NOV, "menu", 7, None, PAGE_SIZE + 1)
    with pytest.raises(VisitInputError):
        await w.list("menu")
    assert w.sales.calls == ["list_visits"]                                     # 422 는 저장소를 부르지 않는다


async def test_줄마다_방문과_날짜와_아이와_금액을_준다():
    w = _World()
    w.sales.visit_rows = [
        SalesVisitRow(9, kst(11, 5, 11), date(2026, 11, 5), 101, 1, 30_000),
        SalesVisitRow(8, kst(11, 4, 11), date(2026, 11, 4), None, 1, None),      # 보호자만의 방문
        SalesVisitRow(7, kst(11, 3, 11), date(2026, 11, 3), 999, 1, None),       # 지운 아이
    ]
    view = await w.list()
    assert [(i.visit_id, i.date, i.pet, i.amount) for i in view.items] == [
        (9, date(2026, 11, 5), PetCard(101, "아이101", None), 30_000),
        (8, date(2026, 11, 4), None, None),
        (7, date(2026, 11, 3), None, None),
    ]
    assert view.next_cursor is None


async def test_익명화한_고객의_방문도_줄은_남고_아이만_없다():
    w = _World()
    w.directory.pet_names[102] = None
    w.rows(1, pet_id=102)
    [item] = (await w.list()).items
    assert (item.visit_id, item.pet) == (1000, None)


async def test_20개씩_주고_더_있으면_다음_쪽_표시를_준다():
    w = _World()
    w.rows(PAGE_SIZE + 5)
    first = await w.list()
    assert len(first.items) == PAGE_SIZE
    last = w.sales.visit_rows[PAGE_SIZE - 1]
    assert decode_visit_cursor(first.next_cursor) == (last.starts_at, last.visit_id)
    second = await w.list(cursor=first.next_cursor)
    assert [i.visit_id for i in second.items] == [r.visit_id for r in w.sales.visit_rows[PAGE_SIZE:]]
    assert second.next_cursor is None
    assert w.sales.visit_args[4] == (last.starts_at, last.visit_id)


async def test_딱_20개면_다음_쪽이_없다():
    w = _World()
    w.rows(PAGE_SIZE)
    assert (await w.list()).next_cursor is None


async def test_깨진_쪽_표시와_범위_밖_anchor_는_422_이고_저장소를_부르지_않는다():
    w = _World()
    with pytest.raises(VisitInputError):
        await w.list(cursor="!!!!")
    with pytest.raises(VisitInputError):
        await w.list(anchor=date(2101, 1, 1))
    assert w.sales.calls == []


async def test_anchor_로_기간을_고르고_앞날의_기간은_빈_목록이다():
    w = _World()
    view = await w.list(span="week", anchor=date(2026, 12, 25))
    assert (view.items, view.next_cursor) == ([], None)
    assert w.sales.visit_args[:2] == (date(2026, 12, 21), date(2026, 12, 28))
