import asyncio
from datetime import date, time

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS, ScheduleSettings
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _menus(session, shop_id=1):
    return (await session.execute(
        text("SELECT name, default_duration_minutes FROM service_menus WHERE shop_id = :s ORDER BY sort_order"),
        {"s": shop_id})).all()


async def test_처음_쓰면_기본_설정과_기본_메뉴가_생긴다(db_session):
    settings = await SchedulePgRepository(db_session).ensure(A)
    assert settings == DEFAULT_SETTINGS
    assert await _menus(db_session) == [("목욕", 60), ("위생", 60), ("부분 미용", 90), ("전체 미용", 150),
                                        ("스포팅", 120)]


async def test_두_번_준비해도_메뉴는_한_번만_들어간다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.ensure(A)
    assert len(await _menus(db_session)) == 5


async def test_두_세션이_동시에_처음_써도_메뉴는_한_번만_들어간다(db_engine):
    """늦은 쪽은 설정 행 INSERT 에서 앞선 쪽의 커밋을 기다렸다가 DO NOTHING 이 된다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as first, factory() as second:
        await SchedulePgRepository(first).ensure(A)
        late = asyncio.create_task(SchedulePgRepository(second).ensure(A))
        await asyncio.sleep(0.3)
        assert not late.done()
        await first.commit()
        assert await late == DEFAULT_SETTINGS
        await second.commit()
    async with factory() as check:
        assert len(await _menus(check)) == 5


async def test_설정을_통째로_바꾼다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.update(A, ScheduleSettings(time(9, 30), time(18), 90, frozenset({0, 6})))
    changed = await repo.update(A, ScheduleSettings(time(9, 30), time(18), 90, frozenset({1})))
    assert changed == ScheduleSettings(time(9, 30), time(18), 90, frozenset({1}))


async def test_매장마다_따로다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.ensure(B)
    await repo.update(A, ScheduleSettings(time(9), time(18), 60, frozenset({0})))
    assert await repo.ensure(B) == DEFAULT_SETTINGS
    await repo.add_closed_date(A, date(2026, 10, 9), "한글날")
    assert await repo.list_closed_dates(B, date(2026, 1, 1), date(2026, 12, 31)) == []
    await repo.delete_closed_date(B, date(2026, 10, 9))   # 다른 매장 컨텍스트로는 지우지 못한다
    assert len(await repo.list_closed_dates(A, date(2026, 1, 1), date(2026, 12, 31))) == 1


async def test_임시_휴무는_두_번_넣어도_하나고_처음_메모를_지킨다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.add_closed_date(A, date(2026, 10, 9), "한글날")
    again = await repo.add_closed_date(A, date(2026, 10, 9), "다른 메모")
    assert (again.day, again.note) == (date(2026, 10, 9), "한글날")
    await repo.add_closed_date(A, date(2026, 10, 3), None)
    found = await repo.list_closed_dates(A, date(2026, 10, 1), date(2026, 10, 9))
    assert [c.day for c in found] == [date(2026, 10, 3), date(2026, 10, 9)]
    await repo.delete_closed_date(A, date(2026, 10, 3))
    await repo.delete_closed_date(A, date(2026, 10, 3))
    assert [c.day for c in await repo.list_closed_dates(A, date(2026, 10, 1), date(2026, 10, 31))] == [
        date(2026, 10, 9)]


async def test_두_사장이_동시에_쉬는_요일을_바꿔도_늦은_쪽이_앞선_쪽을_덮는다(db_engine):
    """늦은 쪽은 설정 행 UPDATE 에서 기다렸다가, 앞선 쪽이 커밋한 쉬는 요일을 지우고 자기 것을 넣는다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        await SchedulePgRepository(setup).ensure(A)
        await setup.commit()
    async with factory() as first, factory() as second:
        await SchedulePgRepository(first).update(A, ScheduleSettings(time(10), time(19), 120, frozenset({0, 1})))
        late = asyncio.create_task(
            SchedulePgRepository(second).update(A, ScheduleSettings(time(9), time(18), 90, frozenset({1, 2})))
        )
        await asyncio.sleep(0.3)
        assert not late.done()
        await first.commit()
        assert (await late).closed_weekdays == frozenset({1, 2})
        await second.commit()
    async with factory() as check:
        assert await SchedulePgRepository(check).ensure(A) == ScheduleSettings(time(9), time(18), 90, frozenset({1, 2}))
