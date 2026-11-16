from dataclasses import replace
from datetime import date, timedelta

import pytest

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.get_day_wrap_up_dto import GetDayWrapUpQuery
from visit.app.use_cases.get_day_wrap_up_interactor import GetDayWrapUpInteractor
from visit.domain.entities.visit_record import RecordItem
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.revisit_settings import RevisitSettings
from visit.tests.helpers.builders import TZ, ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeRevisitSettingsRepository,
    FakeVisits,
)

NOW = kst(9, 23, 15)
YESTERDAY = date(2026, 9, 22)


class _World:
    def __init__(self) -> None:
        self.visits, self.directory, self.menus = FakeVisits(), FakeDirectory(), FakeMenus()
        self.records, self.library = FakeRecords(self.visits), FakeLibrary()
        self.reports, self.settings = FakeReportRepository(self.visits), FakeRevisitSettingsRepository()
        self.directory.family(1, pets=(101, 102))
        self.directory.family(2, pets=(201,))
        self.directory.family(3, pets=(301,), name=None)   # 익명화한 고객
        self.directory.family(4, pets=(401, 402), name="박하나")
        self.interactor = GetDayWrapUpInteractor(
            board=self.visits, menus=self.menus, directory=self.directory, records=self.records,
            library=self.library, reports=self.reports, revisit_settings=self.settings, now=lambda: NOW)

    def done(self, hour, pet_id=101, customer_id=1, day=22, rec=None, **fields) -> int:
        at = kst(9, day, hour)
        found = self.visits.seed(customer_id=customer_id, pet_id=pet_id, starts_at=at, status="completed",
                                 started_at=at, completed_at=at + timedelta(hours=1), **fields)
        if rec is not None:
            self.records.seed(record(found.id, **rec))
        return found.id

    async def sent(self, visit_id) -> None:
        await self.reports.create(ctx(), visit_id, bytes(16), NOW - timedelta(days=1), NOW - timedelta(days=8))

    async def wrap_up(self, day=YESTERDAY, context=None):
        return await self.interactor.get_day_wrap_up(GetDayWrapUpQuery(ctx=context or ctx(), day=day))


def _kinds(view):
    return [(c.kind, c.visit.visit_id) for c in view.cards]


async def test_정리_안_된_예약_결제_안_적음_알림장_안_보냄_차례이고_종류_안에서는_시작_순이다():
    w = _World()
    reserved = w.visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 22, 16)).id
    bare = w.done(11)                                                           # 기록 없음 — 결제만
    total_only = w.done(9, pet_id=102, rec={"total_amount": 30_000})            # 결제·알림장
    paid = w.done(13, pet_id=201, customer_id=2, rec={"total_amount": 30_000, "payment_method": "card"})
    finished = w.done(14, rec={"total_amount": 0})                              # 0원 — 결제 완료
    await w.sent(finished)                                                      # 보낸 적이 있다(이미 닫힘)
    w.visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 22, 10), status="canceled",
                  canceled_at=kst(9, 21, 9), cancel_reason="customer_request")
    w.done(10, pet_id=201, customer_id=2, shop_id=2)                            # 다른 매장
    view = await w.wrap_up()
    assert view.date == YESTERDAY
    assert _kinds(view) == [
        ("unresolved", reserved), ("unpaid", total_only), ("unpaid", bare),
        ("report_unsent", total_only), ("report_unsent", paid)]


async def test_권한이_없는_종류의_장은_나오지_않는다():
    w = _World()
    w.visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 22, 16))
    visit_id = w.done(11, rec={"total_amount": 30_000})
    only_record = ShopContext(shop_id=1, member_id=12, role="staff", permissions=frozenset({"record:write"}),
                              timezone=TZ)
    assert _kinds(await w.wrap_up(context=only_record)) == [("report_unsent", visit_id)]
    nothing = replace(only_record, permissions=frozenset())
    assert (await w.wrap_up(context=nothing)).cards == []


async def test_결제_장은_총액과_결제_수단을_채워_둔다():
    w = _World()
    trim, bath, unpriced = w.menus.seed("전체 미용", price=40_000), w.menus.seed("목욕", price=25_000), \
        w.menus.seed("발톱", price=None)
    w.done(10, day=20, rec={"total_amount": 30_000, "payment_method": "transfer"})            # 그 전 — 계좌이체
    w.done(10, day=21, pet_id=102, rec={"total_amount": 30_000, "payment_method": "cash"})   # 지난번 — 현금
    recorded = w.done(9, rec={"total_amount": 35_000, "payment_method": None})
    itemized = w.done(10, pet_id=201, customer_id=2, rec={
        "items": (RecordItem(trim.id, 38_000), RecordItem(bath.id, 2_000)), "payment_method": "card"})
    menus_only = w.done(11, pet_id=401, customer_id=4, menu_ids=(trim.id, bath.id, unpriced.id))
    nothing = w.done(12, pet_id=402, customer_id=4, menu_ids=(unpriced.id,))
    cards = {c.visit.visit_id: c for c in (await w.wrap_up()).cards if c.kind == "unpaid"}
    prefill = {visit_id: (c.prefill.total_amount, c.prefill.payment_method) for visit_id, c in cards.items()}
    assert prefill == {
        recorded: (35_000, "cash"),       # 기록의 총액, 수단은 그 고객이 지난번에 쓴 것
        itemized: (40_000, "card"),       # 총액이 없으면 기록의 항목 합, 수단은 기록의 것
        menus_only: (65_000, None),       # 기록이 없으면 메뉴 값의 합(값 없는 메뉴는 빼고), 쓴 수단이 없다
        nothing: (None, None),            # 근거가 없으면 비운다 — 앱이 그 자리에서 묻는다
    }
    assert all(c.prefill is None for c in (await w.wrap_up()).cards if c.kind != "unpaid")


async def test_넘긴_알림장과_세지_않기로_한_매장은_알림장_장이_없다():
    w = _World()
    skipped = w.done(11, rec={"total_amount": 0}, report_skipped_at=NOW)
    kept = w.done(12, pet_id=102, rec={"total_amount": 0})
    assert _kinds(await w.wrap_up()) == [("report_unsent", kept)]
    assert skipped != kept
    w.settings.rows[1] = RevisitSettings(count_unsent_reports=False)
    assert (await w.wrap_up()).cards == []


async def test_익명화한_고객의_방문은_남은_일이_아니다():
    w = _World()
    w.done(11, pet_id=301, customer_id=3, rec={"total_amount": 30_000})
    assert (await w.wrap_up()).cards == []


async def test_장의_사진은_아이의_프로필_사진이다():
    w = _World()
    w.library.add(7001)
    w.done(10, day=20, rec={"total_amount": 0, "media": ((7001, "photo", "after", 0),)})   # 그 아이의 지난 사진
    today_visit = w.done(11, rec={"total_amount": 30_000})
    other = w.done(12, pet_id=102, rec={"total_amount": 30_000})
    cards = {c.visit.visit_id: c.photo_url for c in (await w.wrap_up()).cards}
    assert cards == {today_visit: "t/7001", other: None}


async def test_오늘도_열리고_앞날은_빈_목록이다():
    w = _World()
    today = w.done(9, day=23, rec={"total_amount": 30_000, "payment_method": "card"})
    assert _kinds(await w.wrap_up(day=date(2026, 9, 23))) == [("report_unsent", today)]
    w.done(9, day=24, rec={"total_amount": 30_000})   # 일찍 끝낸 내일 방문이어도
    assert (await w.wrap_up(day=date(2026, 9, 24))).cards == []


async def test_범위_밖의_날은_422():
    w = _World()
    with pytest.raises(VisitInputError):
        await w.wrap_up(day=date(1999, 12, 31))
