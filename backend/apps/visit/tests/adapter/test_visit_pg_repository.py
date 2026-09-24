from datetime import timedelta

import pytest

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
from visit.domain.state.visit_state import StatusChange
from visit.domain.value_objects.new_visit import NewVisit
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


def new(pet_id=101, customer_id=1, starts_at=None, minutes=90, status="reserved", started_at=None, menu_ids=()):
    return NewVisit(customer_id=customer_id, pet_id=pet_id, starts_at=starts_at or kst(10, 2, 14),
                    duration_minutes=minutes, status=status, started_at=started_at, menu_ids=menu_ids,
                    memo=None, created_by_member_id=11)


async def _menu_ids(session, shop=A):
    await SchedulePgRepository(session).ensure(shop)
    return [m.id for m in await MenuPgRepository(session).list(shop, include_archived=False)]


async def test_한_번에_넣고_메뉴와_함께_읽는다(db_session):
    bath, trim, *_ = await _menu_ids(db_session)
    visits = await VisitPgRepository(db_session).create_many(
        A, [new(101, menu_ids=(bath, trim)), new(102, menu_ids=(bath, trim))])
    assert [(v.pet_id, v.status, v.menu_ids, v.shop_id) for v in visits] == [
        (101, "reserved", (bath, trim), 1), (102, "reserved", (bath, trim), 1)]


async def test_지금_시작한_손님은_상태를_바꾼_멤버가_만든_사람이다(db_session):
    [visit] = await VisitPgRepository(db_session).create_many(
        A, [new(status="in_progress", started_at=kst(10, 2, 14, 3))])
    assert (visit.status, visit.started_at, visit.status_changed_by_member_id) == (
        "in_progress", kst(10, 2, 14, 3), 11)


async def test_같은_시각의_중복은_VISIT_DUPLICATE_이고_세션은_계속_쓴다(db_session):
    """V5 — 한 번에 넣는 묶음 가운데 하나라도 걸리면 묶음 전체가 들어가지 않는다."""
    repo = VisitPgRepository(db_session)
    await repo.create_many(A, [new(101)])
    with pytest.raises(VisitDuplicateError):
        await repo.create_many(A, [new(102), new(101)])
    with pytest.raises(VisitDuplicateError):
        await repo.create_many(A, [new(None), new(None)])   # 보호자만의 방문도 보호자·시각으로 하나
    occupied = await repo.list_occupied(A, kst(10, 2), kst(10, 3))
    assert [v.pet_id for v in occupied] == [101]


async def test_시간이_겹치는_살아_있는_방문만(db_session):
    repo = VisitPgRepository(db_session)
    await repo.create_many(A, [new(101, starts_at=kst(10, 1, 20), minutes=240)])     # 전날 밤 → 자정에 끝
    await repo.create_many(A, [new(102, starts_at=kst(10, 2, 10))])
    await repo.create_many(A, [new(103, starts_at=kst(10, 2, 23, 50), minutes=10)])
    await repo.create_many(B, [new(104, starts_at=kst(10, 2, 11))])                    # 다른 매장
    await repo.create_many(A, [new(105, starts_at=kst(10, 3, 0))])                     # 다음 날
    occupied = await repo.list_occupied(A, kst(10, 2), kst(10, 3))
    assert [v.pet_id for v in occupied] == [102, 103]   # 전날 밤 방문은 딱 0시에 끝나 겹치지 않는다
    long_before = await repo.list_occupied(A, kst(10, 1, 23), kst(10, 1, 23) + timedelta(hours=1))
    assert [v.pet_id for v in long_before] == [101]


async def test_시작_시각이_구간_안인_방문은_상태와_상관없이(db_session):
    repo = VisitPgRepository(db_session)
    await repo.create_many(A, [new(101, starts_at=kst(10, 2, 10))])
    await repo.create_many(A, [new(102, starts_at=kst(10, 2, 10), status="in_progress",
                                   started_at=kst(10, 2, 10))])
    await repo.create_many(A, [new(103, starts_at=kst(10, 1, 23))])
    await repo.create_many(B, [new(104, starts_at=kst(10, 2, 11))])
    found = await repo.list_between(A, kst(10, 2), kst(10, 3))
    assert [(v.pet_id, v.status) for v in found] == [(101, "reserved"), (102, "in_progress")]


async def test_정리_안_된_예약의_수와_가장_이른_시각(db_session):
    repo = VisitPgRepository(db_session)
    await repo.create_many(A, [new(101, starts_at=kst(7, 14, 10))])
    await repo.create_many(A, [new(102, starts_at=kst(9, 22, 10))])
    await repo.create_many(A, [new(103, starts_at=kst(9, 21, 10), status="in_progress",
                                   started_at=kst(9, 21, 10))])      # 미용 중은 정리 안 됨이 아니다
    await repo.create_many(A, [new(104, starts_at=kst(9, 23, 10))])  # 오늘
    await repo.create_many(B, [new(105, starts_at=kst(6, 1, 10))])
    assert await repo.unresolved_before(A, kst(9, 23)) == (2, kst(7, 14, 10))
    assert await repo.unresolved_before(A, kst(7, 1)) == (0, None)


async def test_하나와_여럿을_읽고_다른_매장은_없다(db_session):
    repo = VisitPgRepository(db_session)
    [mine] = await repo.create_many(A, [new(101)])
    [theirs] = await repo.create_many(B, [new(201)])
    assert (await repo.get(A, mine.id)).pet_id == 101
    with pytest.raises(VisitNotFoundError):
        await repo.get(A, theirs.id)
    assert [v.id for v in await repo.get_many(A, [mine.id, theirs.id])] == [mine.id]
    assert [v.id for v in await repo.lock(A, [theirs.id, mine.id])] == [mine.id]


async def test_세부를_통째로_바꾸고_메뉴도_바꾼다(db_session):
    bath, trim, *_ = await _menu_ids(db_session)
    repo = VisitPgRepository(db_session)
    [visit] = await repo.create_many(A, [new(101, menu_ids=(bath,))])
    changed = await repo.update_details(A, visit.id, kst(10, 3, 11), None, 60, (trim,), "발톱")
    assert (changed.starts_at, changed.pet_id, changed.duration_minutes, changed.menu_ids, changed.memo) == (
        kst(10, 3, 11), None, 60, (trim,), "발톱")
    [other] = await repo.create_many(A, [new(102, starts_at=kst(10, 5, 10))])
    with pytest.raises(VisitDuplicateError):
        await repo.update_details(A, other.id, kst(10, 3, 11), None, 60, (), None)   # 보호자만의 같은 시각


async def test_옮기기가_하나라도_겹치면_모두_되돌린다(db_session):
    repo = VisitPgRepository(db_session)
    kong, bori = await repo.create_many(A, [new(101), new(102)])
    await repo.create_many(A, [new(102, starts_at=kst(10, 3, 15))])
    with pytest.raises(VisitDuplicateError):
        await repo.reschedule(A, [kong.id, bori.id], kst(10, 3, 15))
    assert {v.starts_at for v in await repo.get_many(A, [kong.id, bori.id])} == {kst(10, 2, 14)}
    moved = await repo.reschedule(A, [kong.id, bori.id], kst(10, 4, 15))
    assert {v.starts_at for v in moved} == {kst(10, 4, 15)}


async def test_묶음_지난_완료_노쇼_수(db_session):
    repo = VisitPgRepository(db_session)
    await insert_visit(db_session, kst(7, 1, 14), "completed")
    await insert_visit(db_session, kst(8, 1, 14), "completed")
    await insert_visit(db_session, kst(8, 20, 14), "completed", pet_id=None)
    await insert_visit(db_session, kst(9, 1, 14), "no_show")
    await insert_visit(db_session, kst(9, 1, 14), "no_show", shop_id=2)
    await insert_visit(db_session, kst(9, 3, 14), "completed", customer_id=2, pet_id=201)
    kong, bori = await repo.create_many(A, [new(101), new(102)])
    assert [v.id for v in await repo.list_group(A, 1, kst(10, 2, 14))] == [kong.id, bori.id]
    assert (await repo.last_completed_before(A, 1, 101, kst(10, 2, 14))).starts_at == kst(8, 1, 14)
    assert (await repo.last_completed_before(A, 1, None, kst(10, 2, 14))).starts_at == kst(8, 20, 14)
    assert await repo.last_completed_before(A, 1, 102, kst(10, 2, 14)) is None
    assert await repo.count_no_show(A, 1) == 1


async def test_상태_칸을_통째로_바꾸고_바꾼_멤버를_찍는다(db_session):
    repo = VisitPgRepository(db_session)
    kong, bori = await repo.create_many(A, [new(101), new(102)])
    changed = await repo.apply_changes(
        A, [(kong.id, StatusChange("completed", started_at=kst(10, 2, 14), completed_at=kst(10, 2, 15))),
            (bori.id, StatusChange("canceled", canceled_at=kst(10, 2, 9), cancel_reason="shop_reason"))], 12)
    assert [(v.status, v.status_changed_by_member_id) for v in changed] == [("completed", 12), ("canceled", 12)]
    assert await repo.latest_completed_start(A, 1) == kst(10, 2, 14)
    assert await repo.latest_completed_start(B, 1) is None
    back = await repo.apply_changes(A, [(kong.id, StatusChange("reserved"))], 11)
    assert (back[0].status, back[0].started_at, back[0].completed_at) == ("reserved", None, None)
    assert await repo.latest_completed_start(A, 1) is None


async def test_되돌리기가_중복이_되면_VISIT_DUPLICATE_이고_모두_그대로다(db_session):
    repo = VisitPgRepository(db_session)
    canceled = await insert_visit(db_session, kst(10, 2, 14), "canceled")
    await repo.create_many(A, [new(101)])   # 같은 아이·같은 시각의 새 예약
    with pytest.raises(VisitDuplicateError):
        await repo.apply_changes(A, [(canceled, StatusChange("reserved"))], 11)
    assert (await repo.get(A, canceled)).status == "canceled"


async def test_아이의_지난_완료와_완료_시각들(db_session):
    repo = VisitPgRepository(db_session)
    await insert_visit(db_session, kst(8, 1, 14), "completed")
    last = await insert_visit(db_session, kst(9, 2, 14), "completed")
    await insert_visit(db_session, kst(9, 9, 14), "canceled")
    await insert_visit(db_session, kst(9, 3, 14), "completed", shop_id=2)
    await insert_visit(db_session, kst(9, 4, 14), "completed", pet_id=None)
    assert (await repo.last_completed_of_pet(A, 101)).id == last
    assert await repo.last_completed_of_pet(A, 999) is None
    assert await repo.completed_starts(A, 1, 101, limit=2) == [kst(9, 2, 14), kst(8, 1, 14)]
    assert await repo.completed_starts(A, 1, None, limit=2) == [kst(9, 4, 14)]


async def test_장부_질문들(db_session):
    repo = VisitPgRepository(db_session)
    await insert_visit(db_session, kst(9, 1, 14), "canceled", pet_id=101)
    await insert_visit(db_session, kst(9, 20, 14), "reserved", pet_id=102, memo="메모")
    await insert_visit(db_session, kst(10, 2, 14), "reserved", pet_id=102)
    await insert_visit(db_session, kst(10, 2, 14), "reserved", shop_id=2, customer_id=1, pet_id=103, memo="남의")
    assert (await repo.pet_has_visits(A, 101, active_only=False), await repo.pet_has_visits(A, 101, active_only=True)) == (True, False)
    assert await repo.pet_has_visits(A, 103, active_only=False) is False
    assert (await repo.customer_has_active(A, 1), await repo.customer_has_active(A, 2)) == (True, False)
    assert [v.starts_at for v in await repo.list_active_from(A, 1, kst(9, 23), 5)] == [kst(10, 2, 14)]
    await repo.clear_memos(A, 1)
    assert {v.memo for v in await repo.list_between(A, kst(9, 1), kst(11, 1))} == {None}
    assert [v.memo for v in await repo.list_between(B, kst(9, 1), kst(11, 1))] == ["남의"]


async def test_그_아이의_가장_최근_시작한_방문(db_session):
    repo = VisitPgRepository(db_session)
    assert await repo.latest_started_of_pet(A, 101) is None
    await insert_visit(db_session, kst(9, 1, 14), "completed")
    latest = await insert_visit(db_session, kst(9, 20, 14), "in_progress")
    await insert_visit(db_session, kst(9, 25, 14), "reserved")
    await insert_visit(db_session, kst(9, 22, 14), "canceled")
    await insert_visit(db_session, kst(9, 21, 14), "completed", shop_id=2)
    assert await repo.latest_started_of_pet(A, 101) == latest
