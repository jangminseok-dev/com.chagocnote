from datetime import date, timedelta

import pytest

from visit.app.dtos.get_sales_summary_dto import GetSalesSummaryQuery
from visit.app.dtos.list_due_pets_dto import ListDuePetsQuery
from visit.app.services.pet_cards import PetCard
from visit.app.use_cases.get_sales_summary_interactor import GetSalesSummaryInteractor
from visit.app.use_cases.list_due_pets_interactor import PAGE_SIZE, ListDuePetsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.services.sales_cursor import decode_due_cursor
from visit.domain.value_objects.sales import DuePet
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeSalesGoalRepository,
    FakeSalesRepository,
    FakeVisits,
)

NOW = kst(11, 14, 15)


class _World:
    def __init__(self):
        self.sales, self.directory, self.visits, self.library = (
            FakeSalesRepository(), FakeDirectory(), FakeVisits(), FakeLibrary())
        self.records = FakeRecords(self.visits)
        self.directory.family(1, pets=tuple(range(101, 141)))
        self.interactor = ListDuePetsInteractor(
            sales=self.sales, directory=self.directory, records=self.records, library=self.library,
            now=lambda: NOW)

    async def list(self, cursor=None):
        return await self.interactor.list_due_pets(ListDuePetsQuery(ctx=ctx(), cursor=cursor))


async def test_오래된_순으로_아이와_마지막_방문일을_준다():
    w = _World()
    w.sales.due = [DuePet(102, date(2026, 8, 1)), DuePet(101, date(2026, 9, 1))]
    view = await w.list()
    assert [(i.pet, i.last_visit_date) for i in view.items] == [
        (PetCard(102, "아이102", None), date(2026, 8, 1)),
        (PetCard(101, "아이101", None), date(2026, 9, 1)),
    ]
    assert view.next_cursor is None
    # 오늘 예약이 있는 아이는 그 시각이 지났어도 뺀다 — 저장소에 오늘 0시를 넘긴다.
    assert w.sales.due_args == (date(2026, 11, 14), kst(11, 14, 0))


async def test_무지개다리를_건넌_아이와_익명화한_고객의_아이와_지운_아이는_빠진다():
    w = _World()
    w.directory.family(2, pets=(201, 202), passed=(202,))
    w.directory.family(3, pets=(301,), shop_id=2)            # 다른 매장
    w.directory.pet_names[102] = None                        # 익명화
    w.sales.due = [DuePet(101, date(2026, 8, 1)), DuePet(102, date(2026, 8, 2)), DuePet(202, date(2026, 8, 3)),
                   DuePet(999, date(2026, 8, 4)), DuePet(301, date(2026, 8, 5)), DuePet(201, date(2026, 8, 6))]
    assert [i.pet.pet_id for i in (await w.list()).items] == [101, 201]


async def test_20개씩_주고_쪽_표시로_이어_읽으면_빠지거나_겹치지_않는다():
    w = _World()
    start = date(2026, 6, 1)
    # 같은 날의 아이가 쪽 경계에 걸리게 — 두 마리씩 같은 날.
    w.sales.due = [DuePet(101 + i, start + timedelta(days=i // 2)) for i in range(PAGE_SIZE + 7)]
    first = await w.list()
    assert len(first.items) == PAGE_SIZE
    assert decode_due_cursor(first.next_cursor) == (w.sales.due[PAGE_SIZE - 1].last_day, 101 + PAGE_SIZE - 1)
    second = await w.list(first.next_cursor)
    seen = [i.pet.pet_id for i in first.items + second.items]
    assert seen == [d.pet_id for d in w.sales.due]
    assert second.next_cursor is None


async def test_딱_20마리면_다음_쪽이_없다():
    w = _World()
    w.sales.due = [DuePet(101 + i, date(2026, 6, 1) + timedelta(days=i)) for i in range(PAGE_SIZE)]
    assert (await w.list()).next_cursor is None


async def test_없으면_빈_목록이다():
    view = await _World().list()
    assert (view.items, view.next_cursor) == ([], None)


async def test_깨진_쪽_표시는_422_이고_저장소를_부르지_않는다():
    w = _World()
    with pytest.raises(VisitInputError):
        await w.list("!!!!")
    assert w.sales.calls == []


async def test_요약의_수와_목록의_길이가_같다():
    """요약과 목록이 같은 거르기를 쓴다 — 수가 7 인데 목록이 5 줄이면 안 된다."""
    w = _World()
    w.directory.family(2, pets=(201, 202), passed=(202,))
    w.directory.pet_names[102] = None
    w.sales.due = [DuePet(101, date(2026, 8, 1)), DuePet(102, date(2026, 8, 2)), DuePet(202, date(2026, 8, 3)),
                   DuePet(999, date(2026, 8, 4)), DuePet(201, date(2026, 8, 5)), DuePet(103, date(2026, 8, 6))]
    summary = await GetSalesSummaryInteractor(
        sales=w.sales, goals=FakeSalesGoalRepository(), menus=FakeMenus(), directory=w.directory,
        records=w.records, library=w.library, now=lambda: NOW,
    ).get_sales_summary(GetSalesSummaryQuery(ctx=ctx(), span="month", anchor=None))
    assert summary.due_pet_count == len((await w.list()).items) == 3
