"""마이그레이션 0006 의 제약 — 상태와 시각·사유의 짝, 소요 규칙, 중복 예약, 메뉴 이름."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from visit.tests.helpers.builders import kst

pytestmark = pytest.mark.integration

_INSERT = (
    "INSERT INTO visits (shop_id, customer_id, pet_id, starts_at, duration_minutes, status, "
    "started_at, completed_at, canceled_at, cancel_reason, created_by_member_id) VALUES "
    "(1, :customer, :pet, :starts, :minutes, :status, :started, :completed, :canceled, :reason, 11)"
)
START = kst(9, 23, 14)


def _row(**overrides):
    row = dict(customer=1, pet=101, starts=START, minutes=90, status="reserved", started=None,
               completed=None, canceled=None, reason=None)
    row.update(overrides)
    return row


async def _insert(session, **overrides):
    await session.execute(text(_INSERT), _row(**overrides))


async def _violates(session, **overrides) -> str:
    with pytest.raises(IntegrityError) as caught:
        async with session.begin_nested():
            await _insert(session, **overrides)
    return caught.value.orig.__cause__.constraint_name


async def test_상태와_시각_사유는_짝이_맞아야_한다(db_session):
    await _insert(db_session, status="completed", started=START, completed=START)
    await _insert(db_session, status="canceled", canceled=START, reason="shop_reason")
    assert await _violates(db_session, status="completed", started=START) == "ck_visits_completed_at"
    assert await _violates(db_session, status="canceled", canceled=START) == "ck_visits_canceled_fields"
    assert await _violates(db_session, status="reserved", canceled=START, reason="shop_reason") == (
        "ck_visits_canceled_fields"
    )
    assert await _violates(db_session, status="in_progress") == "ck_visits_started_at"
    assert await _violates(db_session, status="reserved", started=START) == "ck_visits_started_at"
    assert await _violates(db_session, status="waiting") == "ck_visits_status"
    assert await _violates(db_session, status="canceled", canceled=START, reason="weather") == (
        "ck_visits_cancel_reason"
    )


@pytest.mark.parametrize("minutes", [0, 5, 95, 610])
async def test_소요는_10분_단위로_10분에서_600분(db_session, minutes):
    assert await _violates(db_session, minutes=minutes) == "ck_visits_duration"


async def test_같은_반려동물의_같은_시각에는_살아_있는_예약이_하나다(db_session):
    await _insert(db_session)
    assert await _violates(db_session) == "uq_visits_pet_start_active"
    assert await _violates(db_session, status="in_progress", started=START) == "uq_visits_pet_start_active"
    # 취소·노쇼·완료된 방문과는 겹쳐도 된다 — 취소한 자리에 다시 예약한다.
    await _insert(db_session, status="canceled", canceled=START, reason="customer_request")
    await _insert(db_session, status="no_show")
    await _insert(db_session, pet=102)   # 같은 시각의 형제는 된다(가족 묶음)


async def test_보호자만의_예약은_보호자와_시각으로_하나다(db_session):
    await _insert(db_session, pet=None)
    assert await _violates(db_session, pet=None) == "uq_visits_customer_start_active"
    await _insert(db_session, pet=101)   # 같은 보호자의 반려동물 예약과는 다른 것이다


async def _settings(session, shop_id=1):
    await session.execute(
        text("INSERT INTO visit_shop_settings (shop_id, opens_at, closes_at, default_duration_minutes) "
             "VALUES (:shop, '10:00', '19:00', 120)"),
        {"shop": shop_id},
    )


async def test_매장_설정의_규칙(db_session):
    with pytest.raises(IntegrityError) as caught:
        async with db_session.begin_nested():
            await db_session.execute(text(
                "INSERT INTO visit_shop_settings (shop_id, opens_at, closes_at, default_duration_minutes) "
                "VALUES (1, '19:00', '10:00', 120)"))
    assert caught.value.orig.__cause__.constraint_name == "ck_visit_shop_settings_hours"
    await _settings(db_session)
    with pytest.raises(IntegrityError) as caught:
        async with db_session.begin_nested():
            await db_session.execute(text("INSERT INTO visit_weekly_closures VALUES (1, 7)"))
    assert caught.value.orig.__cause__.constraint_name == "ck_visit_weekly_closures_weekday"


async def test_보관하지_않은_메뉴끼리_이름이_겹치지_않는다(db_session):
    await _settings(db_session)
    add = ("INSERT INTO service_menus (shop_id, name, sort_order, archived_at) "
           "VALUES (1, '목욕', 1, CASE WHEN :archived THEN now() END)")
    await db_session.execute(text(add), {"archived": True})
    await db_session.execute(text(add), {"archived": False})
    with pytest.raises(IntegrityError) as caught:
        async with db_session.begin_nested():
            await db_session.execute(text(add), {"archived": False})
    assert caught.value.orig.__cause__.constraint_name == "uq_service_menus_shop_name_active"


async def test_검색_줄에_마지막_방문_시각_칸이_있다(db_session):
    column = (await db_session.execute(text(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'customer_search_entries' AND column_name = 'last_visit_at'"
    ))).scalar_one()
    assert column == "YES"
