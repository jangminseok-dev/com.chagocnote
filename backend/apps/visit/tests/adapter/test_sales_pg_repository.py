"""매출 집계 저장소 — 실제 PostgreSQL 에서 날짜 자르기·합·쪽 나눔을 본다(설계 ⑧ 3.1)."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import insert

from visit.adapter.outbound.orm.visit_orm import (
    ServiceMenuOrm,
    VisitMenuOrm,
    VisitRecordItemOrm,
    VisitRecordOrm,
    VisitReportOrm,
)
from visit.adapter.outbound.pg.sales_pg_repository import SalesPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.value_objects.sales import (
    DaySales,
    DuePet,
    MenuSales,
    PetVisits,
    RemainingBookings,
    SalesTotals,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOV = (date(2026, 11, 1), date(2026, 12, 1))     # 11월 — 첫날과 끝 다음 날
SEOUL = ZoneInfo("Asia/Seoul")


def seoul(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=SEOUL).astimezone(timezone.utc)


async def _record(session, visit_id: int, total: int | None = None, method: str | None = "card",
                  items: dict[int, int] | None = None) -> None:
    await session.execute(insert(VisitRecordOrm).values(
        visit_id=visit_id, total_amount=total, payment_method=method,
        created_by_member_id=11, updated_by_member_id=11,
    ))
    for menu_id, amount in (items or {}).items():
        await session.execute(insert(VisitRecordItemOrm).values(visit_id=visit_id, menu_id=menu_id, amount=amount))


async def _done(session, at: datetime, total: int | None = None, method: str | None = "card",
                items: dict[int, int] | None = None, record: bool = True, **visit_fields) -> int:
    """완료한 방문 하나와 그 기록."""
    visit_id = await insert_visit(session, at, "completed", **visit_fields)
    if record:
        await _record(session, visit_id, total, method, items)
    return visit_id


async def _menus(session, shop=A, **prices: int | None) -> dict[str, int]:
    """이름 → 메뉴 ID. 값은 정가(None 이면 가격 미정). 설정 행이 만드는 기본 메뉴와 이름이 겹치지 않게 접두를 붙인다."""
    await SchedulePgRepository(session).ensure(shop)
    made = {}
    for order, (name, price) in enumerate(prices.items()):
        made[name] = (await session.execute(
            insert(ServiceMenuOrm).values(shop_id=shop.shop_id, name=f"통계 {name}", sort_order=100 + order, price=price)
            .returning(ServiceMenuOrm.id)
        )).scalar_one()
    return made


async def _report(session, visit_id: int, public_id: bytes, viewed: bool = False, revoked: bool = False) -> None:
    at = kst(11, 20, 9)
    await session.execute(insert(VisitReportOrm).values(
        visit_id=visit_id, public_id=public_id, expires_at=None, revoked_at=at if revoked else None,
        first_viewed_at=at if viewed else None, created_by_member_id=11,
    ))


# ---------- 합계 ----------

async def test_완료했고_총액이_있는_방문만_매출이다(db_session):
    repo = SalesPgRepository(db_session)
    await _done(db_session, kst(11, 3, 11), 30_000)
    await _done(db_session, kst(11, 4, 11), 50_000, pet_id=102)
    await _done(db_session, kst(11, 5, 11), None, pet_id=103)              # 기록은 있는데 총액이 없다
    await _done(db_session, kst(11, 6, 11), record=False, pet_id=104)      # 기록이 없다
    await _done(db_session, kst(11, 7, 11), 0, pet_id=105)                 # 0원도 적은 것이다
    await insert_visit(db_session, kst(11, 8, 11), "reserved", pet_id=106)
    in_progress = await insert_visit(db_session, kst(11, 9, 11), "in_progress", pet_id=107)
    await _record(db_session, in_progress, 99_000)                         # 미용 중의 금액은 아직 매출이 아니다
    await insert_visit(db_session, kst(11, 10, 11), "canceled", pet_id=108)
    await insert_visit(db_session, kst(11, 11, 11), "no_show", pet_id=109)
    await insert_visit(db_session, kst(11, 12, 11), "no_show", pet_id=110)

    assert await repo.totals(A, *NOV) == SalesTotals(
        revenue=80_000, completed=5, priced=3, unrecorded=2, no_show=2, canceled=1)


async def test_방문이_없으면_모두_0_이다(db_session):
    assert await SalesPgRepository(db_session).totals(A, *NOV) == SalesTotals(0, 0, 0, 0, 0, 0)
    assert await SalesPgRepository(db_session).by_day(A, *NOV) == []
    assert await SalesPgRepository(db_session).by_payment(A, *NOV) == {}
    assert await SalesPgRepository(db_session).by_menu(A, *NOV) == []
    assert await SalesPgRepository(db_session).pets(A, *NOV) == []
    assert await SalesPgRepository(db_session).report_counts(A, *NOV) == (0, 0)


async def test_다른_매장의_방문은_어디에도_섞이지_않는다(db_session):
    repo = SalesPgRepository(db_session)
    menus = await _menus(db_session, B, 목욕=20_000)
    other = await _done(db_session, kst(11, 3, 11), 70_000, items={menus["목욕"]: 70_000}, shop_id=2)
    await _report(db_session, other, b"\x01" * 16, viewed=True)
    await insert_visit(db_session, kst(11, 25, 11), "reserved", shop_id=2, pet_id=102)

    assert await repo.totals(A, *NOV) == SalesTotals(0, 0, 0, 0, 0, 0)
    assert await repo.by_day(A, *NOV) == []
    assert await repo.by_payment(A, *NOV) == {}
    assert await repo.by_menu(A, *NOV) == []
    assert await repo.pets(A, *NOV) == []
    assert await repo.report_counts(A, *NOV) == (0, 0)
    assert await repo.remaining_reserved(A, kst(11, 14, 15), NOV[1]) == RemainingBookings(0, None)
    assert await repo.list_visits(A, *NOV, "menu", menus["목욕"], None, 20) == []
    assert await repo.due_candidates(A, date(2027, 2, 1), seoul(2027, 2, 1, 9)) == []
    assert (await repo.totals(B, *NOV)).revenue == 70_000


# ---------- 날짜 경계 (Review Focus 1) ----------

async def test_하루의_경계는_매장_시간대다(db_session):
    repo = SalesPgRepository(db_session)
    await _done(db_session, seoul(2026, 11, 13, 23, 30), 10_000)             # UTC 로는 13일 14:30
    await _done(db_session, seoul(2026, 11, 14, 0, 10), 20_000, pet_id=102)  # UTC 로는 13일 15:10 — 그래도 14일의 것
    await _done(db_session, seoul(2026, 11, 14, 23, 59), 40_000, pet_id=103)
    await _done(db_session, seoul(2026, 11, 15, 0, 0), 80_000, pet_id=104)   # 다음 날 0시는 다음 날

    the_14th = (date(2026, 11, 14), date(2026, 11, 15))
    assert (await repo.totals(A, *the_14th)).revenue == 60_000
    assert [(d.day, d.revenue) for d in await repo.by_day(A, date(2026, 11, 13), date(2026, 11, 16))] == [
        (date(2026, 11, 13), 10_000), (date(2026, 11, 14), 60_000), (date(2026, 11, 15), 80_000)]


async def test_달과_해의_경계도_매장_시간대다(db_session):
    repo = SalesPgRepository(db_session)
    await _done(db_session, seoul(2026, 12, 31, 23, 59), 10_000)
    await _done(db_session, seoul(2027, 1, 1, 0, 0), 20_000, pet_id=102)
    await _done(db_session, seoul(2026, 12, 1, 0, 0), 40_000, pet_id=103)
    await _done(db_session, seoul(2026, 11, 30, 23, 59), 80_000, pet_id=104)

    assert (await repo.totals(A, date(2026, 12, 1), date(2027, 1, 1))).revenue == 50_000
    assert (await repo.totals(A, date(2026, 1, 1), date(2027, 1, 1))).revenue == 130_000
    assert (await repo.totals(A, date(2027, 1, 1), date(2028, 1, 1))).revenue == 20_000
    assert (await repo.totals(A, *NOV)).revenue == 80_000


# ---------- 날짜별 ----------

async def test_날짜별_매출과_방문_수_그날의_아이들(db_session):
    repo = SalesPgRepository(db_session)
    await _done(db_session, kst(11, 3, 14), 30_000, pet_id=102)
    await _done(db_session, kst(11, 3, 11), 50_000, pet_id=101)
    await _done(db_session, kst(11, 3, 16), None, pet_id=103)                 # 금액은 없지만 방문은 센다
    await _done(db_session, kst(11, 3, 17), 20_000, pet_id=101, customer_id=1)  # 같은 아이가 하루에 두 번
    await _done(db_session, kst(11, 3, 18), 10_000, pet_id=None)              # 보호자만의 방문
    await _done(db_session, kst(11, 5, 11), 70_000, pet_id=104)
    await insert_visit(db_session, kst(11, 4, 11), "no_show", pet_id=105)     # 완료가 없는 날은 줄이 없다

    assert await repo.by_day(A, *NOV) == [
        DaySales(day=date(2026, 11, 3), revenue=110_000, completed=5, pet_ids=(101, 102, 103)),
        DaySales(day=date(2026, 11, 5), revenue=70_000, completed=1, pet_ids=(104,)),
    ]


async def test_그날의_아이는_다섯까지다(db_session):
    repo = SalesPgRepository(db_session)
    for i in range(7):
        await _done(db_session, kst(11, 3, 9 + i), 10_000, pet_id=201 + i)
    [day] = await repo.by_day(A, *NOV)
    assert (day.completed, day.pet_ids) == (7, (201, 202, 203, 204, 205))


# ---------- 결제 수단·메뉴 ----------

async def test_결제_수단별로_나뉘고_합이_매출과_같다(db_session):
    repo = SalesPgRepository(db_session)
    await _done(db_session, kst(11, 3, 11), 30_000, "card")
    await _done(db_session, kst(11, 4, 11), 20_000, "card", pet_id=102)
    await _done(db_session, kst(11, 5, 11), 50_000, "cash", pet_id=103)
    await _done(db_session, kst(11, 6, 11), 10_000, "transfer", pet_id=104)
    await _done(db_session, kst(11, 7, 11), 7_000, None, pet_id=105)          # 결제 수단을 고르지 않았다
    await _done(db_session, kst(11, 8, 11), None, "cash", pet_id=106)         # 총액이 없으면 수단만으로는 세지 않는다

    payments = await repo.by_payment(A, *NOV)
    assert payments == {"card": 50_000, "cash": 50_000, "transfer": 10_000, None: 7_000}
    assert sum(payments.values()) == (await repo.totals(A, *NOV)).revenue


async def test_메뉴별_항목_합과_건수_가장_최근에_한_아이(db_session):
    repo = SalesPgRepository(db_session)
    menus = await _menus(db_session, 전체미용=50_000, 목욕=20_000, 스파=None)
    full, bath, spa = menus["전체미용"], menus["목욕"], menus["스파"]
    await _done(db_session, kst(11, 3, 11), 60_000, items={full: 50_000, bath: 10_000}, pet_id=101)
    await _done(db_session, kst(11, 9, 11), 45_000, items={full: 50_000}, pet_id=102)       # 할인 — 항목 합이 총액보다 크다
    await _done(db_session, kst(11, 5, 11), 20_000, items={bath: 20_000}, pet_id=103)
    await _done(db_session, kst(11, 6, 11), 30_000, items={}, pet_id=104)                   # 총액만 있고 항목이 없다
    await _done(db_session, kst(11, 7, 11), None, items={spa: 99_000}, pet_id=105)          # 총액이 없으면 항목도 세지 않는다
    await _done(db_session, kst(11, 12, 11), 15_000, items={bath: 15_000}, pet_id=None)     # 보호자만 — 아이는 그 앞 방문의 아이

    assert await repo.by_menu(A, *NOV) == [
        MenuSales(menu_id=full, amount=100_000, count=2, latest_pet_id=102),
        MenuSales(menu_id=bath, amount=45_000, count=3, latest_pet_id=103),
    ]


async def test_메뉴는_금액이_큰_순이고_같으면_ID_순이다(db_session):
    repo = SalesPgRepository(db_session)
    menus = await _menus(db_session, 가=None, 나=None, 다=None)
    await _done(db_session, kst(11, 3, 11), 60_000, items={menus["나"]: 20_000, menus["가"]: 20_000, menus["다"]: 30_000})
    assert [m.menu_id for m in await repo.by_menu(A, *NOV)] == [menus["다"], menus["가"], menus["나"]]


# ---------- 아이 ----------

async def test_기간의_아이마다_방문_수와_마지막_날_그리고_매장에서의_첫_방문일(db_session):
    repo = SalesPgRepository(db_session)
    await _done(db_session, kst(8, 20, 11), 10_000, pet_id=101)       # 8월에 처음 — 11월에는 다시 온 아이
    await _done(db_session, kst(11, 3, 11), 10_000, pet_id=101)
    await _done(db_session, kst(11, 20, 11), 10_000, pet_id=101)
    await _done(db_session, kst(11, 9, 11), 10_000, pet_id=102)       # 11월에 처음
    await insert_visit(db_session, kst(7, 1, 11), "no_show", pet_id=102)    # 노쇼·취소는 첫 방문이 아니다
    await insert_visit(db_session, kst(7, 2, 11), "canceled", pet_id=102)
    await _done(db_session, kst(11, 10, 11), 10_000, pet_id=None)     # 보호자만의 방문은 아이가 아니다
    await _done(db_session, kst(12, 1, 11), 10_000, pet_id=103)       # 기간 밖

    assert await repo.pets(A, *NOV) == [
        PetVisits(pet_id=101, visits=2, last_day=date(2026, 11, 20), first_ever_day=date(2026, 8, 20)),
        PetVisits(pet_id=102, visits=1, last_day=date(2026, 11, 9), first_ever_day=date(2026, 11, 9)),
    ]


# ---------- 예약 ----------

async def test_남은_예약은_지금_이후의_예약만이고_예상_금액은_정가_합이다(db_session):
    repo = SalesPgRepository(db_session)
    menus = await _menus(db_session, 전체미용=50_000, 목욕=20_000, 스파=None)
    now = kst(11, 14, 15)

    async def reserve(at, *names, status="reserved", pet_id=101):
        visit_id = await insert_visit(db_session, at, status, pet_id=pet_id)
        for name in names:
            await db_session.execute(insert(VisitMenuOrm).values(visit_id=visit_id, menu_id=menus[name]))

    await reserve(kst(11, 14, 16), "전체미용", "목욕")              # 오늘 이따
    await reserve(kst(11, 20, 11), "목욕", "스파", pet_id=102)      # 스파는 정가가 없다 — 빼고 더한다
    await reserve(kst(11, 21, 11), pet_id=103)                      # 메뉴를 고르지 않은 예약
    await reserve(kst(11, 14, 14), "전체미용", pet_id=104)          # 오늘 이미 지난 예약
    await reserve(kst(12, 1, 0), "전체미용", pet_id=105)            # 다음 달
    await reserve(kst(11, 22, 11), "전체미용", status="canceled", pet_id=106)

    assert await repo.remaining_reserved(A, now, NOV[1]) == RemainingBookings(count=3, expected_amount=90_000)


async def test_정가가_있는_메뉴가_하나도_없으면_예상_금액은_None_이다(db_session):
    repo = SalesPgRepository(db_session)
    menus = await _menus(db_session, 스파=None)
    visit_id = await insert_visit(db_session, kst(11, 20, 11), "reserved")
    await db_session.execute(insert(VisitMenuOrm).values(visit_id=visit_id, menu_id=menus["스파"]))
    await insert_visit(db_session, kst(11, 21, 11), "reserved", pet_id=102)
    assert await repo.remaining_reserved(A, kst(11, 14, 15), NOV[1]) == RemainingBookings(count=2, expected_amount=None)


# ---------- 알림장 ----------

async def test_알림장은_줄이_있으면_보낸_것이고_하나라도_열었으면_연_것이다(db_session):
    repo = SalesPgRepository(db_session)
    sent = await _done(db_session, kst(11, 3, 11), 10_000, pet_id=101)
    await _report(db_session, sent, b"\x01" * 16)
    opened = await _done(db_session, kst(11, 4, 11), 10_000, pet_id=102)
    await _report(db_session, opened, b"\x02" * 16, viewed=True)
    resent = await _done(db_session, kst(11, 5, 11), 10_000, pet_id=103)     # 끊고 다시 보내 줄이 둘 — 방문은 하나
    await _report(db_session, resent, b"\x03" * 16, viewed=True, revoked=True)
    await _report(db_session, resent, b"\x04" * 16)
    closed = await _done(db_session, kst(11, 6, 11), 10_000, pet_id=104)     # 끊은 줄만 남은 방문도 보낸 것이다
    await _report(db_session, closed, b"\x05" * 16, revoked=True)
    await _done(db_session, kst(11, 7, 11), 10_000, pet_id=105)              # 보내지 않았다
    outside = await _done(db_session, kst(12, 2, 11), 10_000, pet_id=106)
    await _report(db_session, outside, b"\x06" * 16, viewed=True)

    assert await repo.report_counts(A, *NOV) == (4, 2)


# ---------- 방문 목록 ----------

async def test_방문_목록의_네_종류(db_session):
    repo = SalesPgRepository(db_session)
    menus = await _menus(db_session, 전체미용=None, 목욕=None)
    priced = await _done(db_session, kst(11, 3, 11), 30_000, items={menus["전체미용"]: 30_000}, pet_id=101)
    blank = await _done(db_session, kst(11, 4, 11), None, items={menus["전체미용"]: 30_000}, pet_id=102)
    bare = await _done(db_session, kst(11, 5, 11), record=False, pet_id=103, customer_id=9)
    no_show = await insert_visit(db_session, kst(11, 6, 11), "no_show", pet_id=104)
    canceled = await insert_visit(db_session, kst(11, 7, 11), "canceled", pet_id=None)
    await _done(db_session, kst(11, 8, 11), 20_000, items={menus["목욕"]: 20_000}, pet_id=105)

    def ids(rows):
        return [r.visit_id for r in rows]

    unrecorded = await repo.list_visits(A, *NOV, "unrecorded", None, None, 20)
    assert ids(unrecorded) == [bare, blank]                                  # 최신순
    assert (unrecorded[0].day, unrecorded[0].pet_id, unrecorded[0].customer_id, unrecorded[0].amount) == (
        date(2026, 11, 5), 103, 9, None)
    assert ids(await repo.list_visits(A, *NOV, "no_show", None, None, 20)) == [no_show]
    [row] = await repo.list_visits(A, *NOV, "canceled", None, None, 20)
    assert (row.visit_id, row.pet_id) == (canceled, None)
    by_menu = await repo.list_visits(A, *NOV, "menu", menus["전체미용"], None, 20)
    assert ids(by_menu) == [priced]                                          # 총액이 없는 기록의 항목은 메뉴 매출이 아니다
    assert by_menu[0].amount == 30_000
    assert await repo.list_visits(A, date(2026, 10, 1), date(2026, 11, 1), "unrecorded", None, None, 20) == []


async def test_방문_목록은_쪽_경계에서_빠지거나_겹치지_않는다(db_session):
    repo = SalesPgRepository(db_session)
    same = kst(11, 5, 11)
    made = [await insert_visit(db_session, same, "no_show", pet_id=300 + i) for i in range(3)]   # 같은 시각의 셋
    made.append(await insert_visit(db_session, kst(11, 4, 11), "no_show", pet_id=310))
    made.append(await insert_visit(db_session, kst(11, 6, 11), "no_show", pet_id=311))

    seen, before = [], None
    while True:
        page = await repo.list_visits(A, *NOV, "no_show", None, before, 2)
        if not page:
            break
        seen += [r.visit_id for r in page]
        before = (page[-1].starts_at, page[-1].visit_id)
    assert seen == [made[4], made[2], made[1], made[0], made[3]]


# ---------- 다시 올 때가 지난 아이 ----------

async def test_다시_올_때가_지난_아이는_57일_전부터_365일_전까지다(db_session):
    repo = SalesPgRepository(db_session)
    today = date(2026, 11, 14)
    now = kst(11, 14, 15)

    def days_ago(n: int) -> datetime:
        d = today - timedelta(days=n)
        return seoul(d.year, d.month, d.day, 11)

    await _done(db_session, days_ago(56), 10_000, pet_id=101)       # 8주 — 아직 아니다
    await _done(db_session, days_ago(57), 10_000, pet_id=102)       # 8주가 넘었다
    await _done(db_session, days_ago(365), 10_000, pet_id=103)
    await _done(db_session, days_ago(366), 10_000, pet_id=104)      # 한 해가 넘었다 — 떠난 손님
    await _done(db_session, days_ago(100), 10_000, pet_id=None)     # 보호자만의 방문

    assert await repo.due_candidates(A, today, now) == [
        DuePet(pet_id=103, last_day=today - timedelta(days=365)),
        DuePet(pet_id=102, last_day=today - timedelta(days=57)),
    ]


async def test_다시_올_때는_마지막_완료_방문으로_보고_앞으로의_예약이_있으면_뺀다(db_session):
    repo = SalesPgRepository(db_session)
    today, now = date(2026, 11, 14), kst(11, 14, 15)
    await _done(db_session, kst(8, 1, 11), 10_000, pet_id=101)
    await _done(db_session, kst(11, 1, 11), 10_000, pet_id=101)            # 최근에 왔다 — 빠진다
    await _done(db_session, kst(8, 2, 11), 10_000, pet_id=102)
    await insert_visit(db_session, kst(11, 20, 11), "reserved", pet_id=102)     # 예약이 잡혀 있다 — 빠진다
    await _done(db_session, kst(8, 3, 11), 10_000, pet_id=103)
    await insert_visit(db_session, kst(11, 10, 11), "reserved", pet_id=103)     # 며칠 전에 지나간 예약은 막지 않는다
    await _done(db_session, kst(8, 4, 11), 10_000, pet_id=104)
    await insert_visit(db_session, kst(11, 14, 14), "in_progress", pet_id=104)  # 지금 미용 중이다 — 빠진다
    await _done(db_session, kst(8, 5, 11), 10_000, pet_id=105)
    await insert_visit(db_session, kst(11, 5, 11), "no_show", pet_id=105)       # 그 뒤 노쇼·취소는 온 것이 아니다
    await insert_visit(db_session, kst(11, 6, 11), "canceled", pet_id=105)
    await _done(db_session, kst(8, 5, 15), 10_000, pet_id=106)                  # 같은 날이면 pet_id 순

    assert await repo.due_candidates(A, today, now) == [
        DuePet(pet_id=103, last_day=date(2026, 8, 3)),
        DuePet(pet_id=105, last_day=date(2026, 8, 5)),
        DuePet(pet_id=106, last_day=date(2026, 8, 5)),
    ]
