from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.dtos.visit_events import VisitRescheduled
from visit.app.dtos.build_send_bundle_dto import BundlePartView
from visit.app.dtos.reschedule_visits_dto import RescheduleVisitsCommand
from visit.app.use_cases.reschedule_visits_interactor import RescheduleVisitsInteractor
from visit.domain.errors import (
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotFoundError,
    VisitSeriesConflictError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeEvents,
    FakeMenus,
    FakeSchedule,
    FakeShopProfile,
    FakeVisits,
    Journal,
)

NOW = kst(9, 23, 15)


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102))
    directory.family(2, pets=(201,))
    events = FakeEvents(journal)
    shops = FakeShopProfile({1: ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None,
                                            timezone="Asia/Seoul", open=True)})
    interactor = RescheduleVisitsInteractor(visits, visits, FakeMenus(), FakeSchedule(), directory, events=events,
                                            now=lambda: NOW, shops=shops)
    return journal, visits, interactor, events


def _move(ids, starts_at=kst(10, 3, 15), shop_id=1, **change):
    return RescheduleVisitsCommand(ctx=ctx(shop_id=shop_id), visit_ids=tuple(ids), starts_at=starts_at, **change)


async def test_가족_묶음을_함께_옮긴다():
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=90)
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=120)
    result = await interactor.reschedule_visits(_move([bori.id, kong.id]))
    assert [(v.visit_id, v.starts_at.isoformat()) for v in result.visits] == [
        (kong.id, "2026-10-03T15:00:00+09:00"), (bori.id, "2026-10-03T15:00:00+09:00")]
    assert result.warnings == []
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("lock_visits") < names.index("reschedule")


async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
    """V14"""
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 14))
    with pytest.raises(VisitGroupMismatchError):
        await interactor.reschedule_visits(_move([kong.id, other.id]))
    assert journal == []


async def test_예약됨이_아닌_방문이_있으면_하나도_옮기지_않는다():
    journal, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 14), status="in_progress",
                       started_at=kst(9, 23, 14))
    with pytest.raises(VisitStateConflictError):
        await interactor.reschedule_visits(_move([kong.id, bori.id]))
    assert "reschedule" not in [entry[0] for entry in journal]
    assert events.published == []


async def test_가장_긴_소요로_자정_넘김을_본다():
    _, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=60)
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=180)
    with pytest.raises(VisitCrossesMidnightError):
        await interactor.reschedule_visits(_move([kong.id, bori.id], starts_at=kst(10, 3, 22)))


async def test_없는_방문_범위_밖_시각_중복():
    _, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 3, 15))
    with pytest.raises(VisitNotFoundError):
        await interactor.reschedule_visits(_move([kong.id, 999]))
    with pytest.raises(VisitInputError):
        await interactor.reschedule_visits(_move([kong.id], starts_at=kst(10, 3, 15, 5)))
    with pytest.raises(VisitDuplicateError):
        await interactor.reschedule_visits(_move([kong.id]))
    theirs = visits.seed(customer_id=9, shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.reschedule_visits(_move([theirs.id]))


async def test_옮긴_방문마다_VisitRescheduled_를_옮긴_뒤에_발행한다():
    journal, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    await interactor.reschedule_visits(_move([bori.id, kong.id]))
    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.previous_starts_at, e.starts_at, e.occurred_at,
             e.family_pet_ids)
            for e in events.published] == [
        (VisitRescheduled, ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 15), NOW, (101, 102)),
        (VisitRescheduled, ctx(), bori.id, 1, 102, kst(10, 2, 14), kst(10, 3, 15), NOW, (101, 102))]
    names = [entry[0] for entry in journal]
    assert names.index("reschedule") < names.index("publish")


async def test_옮긴_방문마다_다시_색인하라고_알린다():
    """날짜가 바뀌면 검색 문서의 날짜도 바뀐다."""
    _, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    await interactor.reschedule_visits(_move([kong.id, bori.id]))
    assert events.changed == [("visit", kong.id), ("visit", bori.id)]


# --- ⑭ 이후 전부 ------------------------------------------------------------------------------------------------------

WEEKLY = (kst(10, 2, 14), kst(10, 9, 14), kst(10, 16, 14))


def _weekly(visits, pets=(101,), statuses=None):
    statuses = statuses or {}
    return {(at, pet): visits.seed(customer_id=1, pet_id=pet, starts_at=at, series_id=7,
                                   status=statuses.get((at, pet), "reserved"))
            for at in WEEKLY for pet in pets}


def _following(anchor_ids, starts_at=kst(10, 10, 15), **change):
    return _move(anchor_ids, starts_at=starts_at, scope="following", **change)


async def test_이후_전부를_같은_차이만큼_민다():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits)
    result = await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id]))
    assert [visits.rows[rows[(at, 101)].id].starts_at for at in WEEKLY] == [
        kst(10, 2, 14), kst(10, 10, 15), kst(10, 17, 15)]
    assert sorted(v.visit_id for v in result.visits) == sorted(rows[(at, 101)].id for at in WEEKLY[1:])


async def test_가장_가까운_회차만_변경_안내이고_나머지는_조용히():
    _, visits, interactor, events = _setup()
    rows = _weekly(visits, pets=(101, 102))
    await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id, rows[(WEEKLY[1], 102)].id]))
    moved = [e for e in events.published if isinstance(e, VisitRescheduled)]
    assert sorted((e.previous_starts_at, e.pet_id, e.quiet, e.family_pet_ids) for e in moved) == [
        (WEEKLY[1], 101, False, (101, 102)), (WEEKLY[1], 102, False, (101, 102)),
        (WEEKLY[2], 101, True, (101, 102)), (WEEKLY[2], 102, True, (101, 102))]


async def test_걸린_회차가_있으면_아무것도_바꾸지_않고_VISIT_SERIES_CONFLICT():
    _, visits, interactor, events = _setup()
    rows = _weekly(visits)
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 17, 15))   # 묶음 밖 예약이 셋째 회차의 새 자리에
    before = dict(visits.rows)
    with pytest.raises(VisitSeriesConflictError) as caught:
        await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id]))
    assert caught.value.details == {"conflicts": [{
        "visit_id": rows[(WEEKLY[2], 101)].id, "pet_id": 101, "starts_at": "2026-10-17T15:00:00+09:00",
        "reason": "taken"}]}
    assert visits.rows == before and events.published == [] and events.changed == []


async def test_범위_밖으로_밀리는_회차는_out_of_range_로_걸린다():
    _, visits, interactor, _ = _setup()
    seoul = ZoneInfo("Asia/Seoul")
    first = datetime(2027, 9, 10, 14, tzinfo=seoul)
    a = visits.seed(customer_id=1, pet_id=101, starts_at=first, series_id=7)
    b = visits.seed(customer_id=1, pet_id=101, starts_at=first + timedelta(weeks=1), series_id=7)
    with pytest.raises(VisitSeriesConflictError) as caught:
        await interactor.reschedule_visits(_following([a.id], starts_at=first + timedelta(days=14)))
    assert [(c["visit_id"], c["reason"]) for c in caught.value.details["conflicts"]] == [(b.id, "out_of_range")]
    result = await interactor.reschedule_visits(
        _following([a.id], starts_at=first + timedelta(days=14), skip_visit_ids=(b.id,)))
    assert [v.visit_id for v in result.visits] == [a.id]


async def test_skip_visit_ids_로_걸린_회차를_빼고_옮긴다():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits)
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 17, 15))
    third = rows[(WEEKLY[2], 101)]
    await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id], skip_visit_ids=(third.id,)))
    assert visits.rows[third.id].starts_at == WEEKLY[2]
    assert visits.rows[rows[(WEEKLY[1], 101)].id].starts_at == kst(10, 10, 15)


async def test_family_false_면_그_아이의_뒤_회차만():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits, pets=(101, 102))
    await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id], family=False))
    assert [visits.rows[rows[(at, 102)].id].starts_at for at in WEEKLY] == list(WEEKLY)
    assert visits.rows[rows[(WEEKLY[2], 101)].id].starts_at == kst(10, 17, 15)


async def test_미용_중_완료_취소_앞선_회차는_건드리지_않는다():
    _, visits, interactor, _ = _setup()
    statuses = {(WEEKLY[2], 101): "canceled", (WEEKLY[2], 102): "completed"}
    rows = _weekly(visits, pets=(101, 102), statuses=statuses)
    await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id, rows[(WEEKLY[1], 102)].id]))
    assert visits.rows[rows[(WEEKLY[0], 101)].id].starts_at == WEEKLY[0]
    assert [visits.rows[rows[key].id].starts_at for key in statuses] == [WEEKLY[2], WEEKLY[2]]


async def test_방문마다_검색_이벤트와_notice_에_옮긴_회차가_전부():
    _, visits, interactor, events = _setup()
    rows = _weekly(visits)
    result = await interactor.reschedule_visits(_following([rows[(WEEKLY[1], 101)].id]))
    assert sorted(ref for _, ref in events.changed) == sorted(rows[(at, 101)].id for at in WEEKLY[1:])
    assert result.notice == [BundlePartView(
        kind="series_change",
        text="[Hiss Haus] 예약 날짜를 바꿨어요.\n아이101\n· 10월 10일(토) 오후 3:00\n· 10월 17일(토) 오후 3:00")]


async def test_scope_없는_예전_요청은_지금처럼():
    _, visits, interactor, events = _setup()
    rows = _weekly(visits)
    result = await interactor.reschedule_visits(_move([rows[(WEEKLY[1], 101)].id], starts_at=kst(10, 10, 15)))
    assert result.notice == []
    assert visits.rows[rows[(WEEKLY[2], 101)].id].starts_at == WEEKLY[2]
    [event] = [e for e in events.published if isinstance(e, VisitRescheduled)]
    assert event.quiet is False


async def test_이후_전부의_알림은_옮기는_차례대로_낸다():
    """주마다 묶음을 1주 밀면 2회차가 3회차의 옛 자리로 간다 — 3회차가 먼저 그 자리를 떠나야(알림 묶음 줄에서 빠져야)
    2회차가 새로 단 줄이 지워지지 않는다. 늦게 미는 묶음은 늦은 회차부터 알린다."""
    _, visits, interactor, events = _setup()
    rows = _weekly(visits)
    await interactor.reschedule_visits(_following([rows[(WEEKLY[0], 101)].id], starts_at=WEEKLY[1]))
    assert [e.previous_starts_at for e in events.published if isinstance(e, VisitRescheduled)] == list(reversed(WEEKLY))
