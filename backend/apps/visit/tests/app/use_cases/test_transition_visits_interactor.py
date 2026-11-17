from dataclasses import replace
from datetime import timedelta

import pytest

from hub.app.dtos.pet_revisit import PetRevisitFact
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.dtos.visit_events import VisitCanceled, VisitClosed, VisitReserved
from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.domain.value_objects.revisit_settings import RevisitSettings
from visit.domain.errors import (
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotYetError,
    VisitReportSentError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from hub.app.errors import FamilyPetPassedAwayError
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeEvents,
    FakeMenus,
    FakeReportRepository,
    FakeRevisitSettingsRepository,
    FakeShopProfile,
    FakeVisits,
    Journal,
)

SHOPS = FakeShopProfile({1: ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul",
                                        open=True)})

NOW = kst(9, 23, 15)


def _with_reports(visits=None):
    journal = Journal()
    visits, directory = visits or FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102, 103), passed=(103,))
    directory.family(2, pets=(201,))
    reports = FakeReportRepository(visits)
    events = FakeEvents(journal)
    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), reports, directory, events=events,
                                            now=lambda: NOW, settings=FakeRevisitSettingsRepository(), shops=SHOPS)
    return journal, visits, reports, interactor, events


def _setup():
    journal, visits, _, interactor, events = _with_reports()
    return journal, visits, interactor, events


def _act(ids, action, reason=None, member_id=11, **change):
    return TransitionVisitsCommand(ctx=ctx(member_id=member_id), visit_ids=tuple(ids), action=action,
                                   cancel_reason=reason, **change)


async def test_가족_묶음을_한_번에_완료하고_최근_방문을_알린다():
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
    result = await interactor.transition_visits(_act([kong.id, bori.id], "complete", member_id=12))
    assert [(v.status, v.status_changed_by_member_id) for v in result.visits] == [("completed", 12)] * 2
    assert visits.rows[kong.id].completed_at == NOW
    names = [entry[0] for entry in journal]
    assert names == ["lock_family", "lock_visits", "apply_changes", "set_last_visit", "publish", "publish"]
    assert journal[0] == ("lock_family", 1, ())   # 되돌리기가 아니면 보호자만 잠근다
    assert journal[3:] == [("set_last_visit", 1, kst(9, 23, 13)), ("publish", "VisitClosed", kong.id),
                           ("publish", "VisitClosed", bori.id)]


async def test_완료를_되돌리면_최근_방문을_다시_계산한다():
    journal, visits, interactor, _ = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    today = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13), status="completed",
                        started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))
    await interactor.transition_visits(_act([today.id], "revert"))
    assert visits.rows[today.id].status == "reserved"
    assert journal[0] == ("lock_family", 1, (101,))   # 되돌리기는 아이도 확인한다
    assert journal[-2:] == [("set_last_visit", 1, kst(9, 2, 14)), ("publish", "VisitReserved", today.id)]


async def test_완료와_상관없는_전이는_최근_방문을_건드리지_않는다():
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "cancel", "customer_request"))
    assert "set_last_visit" not in [entry[0] for entry in journal]
    assert (visits.rows[kong.id].status, visits.rows[kong.id].cancel_reason) == ("canceled", "customer_request")


async def test_하나라도_안_되면_아무것도_바꾸지_않는다():
    """V6 — 미용 중과 예약됨이 섞인 묶음에 '시작'을 누르면 둘 다 그대로다."""
    journal, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13), status="in_progress",
                       started_at=kst(9, 23, 13))
    with pytest.raises(VisitStateConflictError):
        await interactor.transition_visits(_act([kong.id, bori.id], "start"))
    assert (visits.rows[kong.id].status, visits.rows[bori.id].status) == ("reserved", "in_progress")
    assert "apply_changes" not in [entry[0] for entry in journal]
    assert events.published == []


async def test_상태_규칙은_도메인이_정한다():
    _, visits, interactor, _ = _setup()
    tomorrow = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 24, 10))
    with pytest.raises(VisitNotYetError):
        await interactor.transition_visits(_act([tomorrow.id], "start"))
    later_today = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 18))
    with pytest.raises(VisitNotYetError):
        await interactor.transition_visits(_act([later_today.id], "no_show"))
    with pytest.raises(VisitInputError):
        await interactor.transition_visits(_act([later_today.id], "cancel"))


async def test_무지개다리_아이의_방문은_되돌리지_못한다():
    """V7 — 되돌리면 다시 앞으로의 예약이 된다."""
    _, visits, interactor, _ = _setup()
    canceled = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="shop_reason")
    with pytest.raises(FamilyPetPassedAwayError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


async def test_되돌린_자리에_이미_새_예약이_있으면_VISIT_DUPLICATE_다():
    _, visits, interactor, _ = _setup()
    canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="customer_request")
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14))
    with pytest.raises(VisitDuplicateError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 13))
    with pytest.raises(VisitGroupMismatchError):
        await interactor.transition_visits(_act([kong.id, other.id], "complete"))
    assert journal == []


class _PetSwapVisits(FakeVisits):
    """잠그는 사이 다른 요청이 그 방문의 반려동물을 바꿔 버린 상황을 흉내 낸다 — get_many 는 옛 값, lock 은 새 값."""

    def __init__(self, journal, swap_visit_id, new_pet_id):
        super().__init__(journal)
        self._swap_visit_id = swap_visit_id
        self._new_pet_id = new_pet_id

    async def lock(self, ctx, visit_ids):
        self.rows[self._swap_visit_id] = replace(self.rows[self._swap_visit_id], pet_id=self._new_pet_id)
        return await super().lock(ctx, visit_ids)


async def test_되돌리기_잠그는_사이_반려동물이_바뀌면_다시_보고_거절한다():
    """가족 확인은 잠그기 전 반려동물로 판단한다 — 잠근 뒤 다시 읽은 값과 다르면 낡은 확인이다(V7 우회 방지)."""
    journal = Journal()
    directory = FakeDirectory(journal)
    directory.family(1, pets=(101, 102, 103), passed=(103,))
    visits = _PetSwapVisits(journal, swap_visit_id=None, new_pet_id=102)
    canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="customer_request")
    visits._swap_visit_id = canceled.id
    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), FakeReportRepository(visits), directory,
                                            events=FakeEvents(journal), now=lambda: NOW,
                                            settings=FakeRevisitSettingsRepository(), shops=SHOPS)
    with pytest.raises(VisitStateConflictError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


def _done(visits, pet_id=101):
    return visits.seed(customer_id=1, pet_id=pet_id, starts_at=kst(9, 23, 13), status="completed",
                       started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))


async def _send(reports, visit_id, expires_at=NOW + timedelta(days=7)):
    """어제 보낸 링크."""
    await reports.create(ctx(), visit_id, bytes(16), expires_at, NOW - timedelta(days=1))


async def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
    journal, visits, reports, interactor, _ = _with_reports()
    sent = _done(visits)
    await _send(reports, sent.id)
    with pytest.raises(VisitReportSentError):
        await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "completed"
    assert [entry[0] for entry in journal] == ["lock_family", "lock_visits"]


async def test_링크를_끊으면_되돌려진다():
    _, visits, reports, interactor, _ = _with_reports()
    sent = _done(visits)
    await _send(reports, sent.id)
    await reports.revoke(ctx(), sent.id, NOW)
    await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "reserved"


async def test_링크의_기간이_지나면_되돌려진다():
    _, visits, reports, interactor, _ = _with_reports()
    sent = _done(visits)
    await _send(reports, sent.id, expires_at=NOW)   # 지금 끝난다
    await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "reserved"


async def test_함께_되돌리는_방문_하나에_알림장이_있으면_둘_다_그대로다():
    journal, visits, reports, interactor, _ = _with_reports()
    kong, bori = _done(visits), _done(visits, pet_id=102)
    await _send(reports, bori.id)
    with pytest.raises(VisitReportSentError):
        await interactor.transition_visits(_act([kong.id, bori.id], "revert"))
    assert (visits.rows[kong.id].status, visits.rows[bori.id].status) == ("completed", "completed")
    assert "apply_changes" not in [entry[0] for entry in journal]


class _SentWhileLocking(FakeVisits):
    """잠금을 기다리는 사이 다른 요청이 알림장을 보낸 상황을 흉내 낸다 — 잠금을 얻었을 때는 링크가 있다."""

    reports: FakeReportRepository

    async def lock(self, ctx, visit_ids):
        for visit_id in visit_ids:
            await _send(self.reports, visit_id)
        return await super().lock(ctx, visit_ids)


async def test_알림장을_보냈는지는_잠근_뒤에_읽는다():
    """R9 — 잠그기 전에 읽으면 '링크 없음'을 보고 되돌려 버린다."""
    _, visits, reports, interactor, _ = _with_reports(_SentWhileLocking())
    visits.reports = reports
    sent = _done(visits)
    with pytest.raises(VisitReportSentError):
        await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "completed"


def _completed(visits, pet_id, month, day, customer_id=1):
    return visits.seed(customer_id=customer_id, pet_id=pet_id, starts_at=kst(month, day, 14), status="completed",
                       started_at=kst(month, day, 14), completed_at=kst(month, day, 15))


async def test_취소는_사유를_실은_VisitCanceled_를_발행한다():
    _, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "cancel", "shop_reason"))
    [event] = events.published
    assert isinstance(event, VisitCanceled)
    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.starts_at, event.occurred_at,
            event.reason) == (ctx(), kong.id, 1, 101, kst(9, 23, 13), NOW, "shop_reason")


async def test_완료는_같은_아이의_앞선_완료_시작_시각을_실은_VisitClosed_를_발행한다():
    """자기 자신은 빼고, 다른 아이·취소는 세지 않고, 보호자만 방문은 보호자만 방문끼리."""
    _, visits, interactor, events = _setup()
    _completed(visits, 101, 8, 1)
    _completed(visits, 101, 9, 2)
    _completed(visits, 102, 9, 10)
    _completed(visits, None, 9, 12)
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 20, 14), status="canceled", canceled_at=NOW,
                cancel_reason="shop_reason")
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    alone = visits.seed(customer_id=1, pet_id=None, starts_at=kst(9, 23, 13))
    first = visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id, alone.id], "complete"))
    await interactor.transition_visits(_act([first.id], "complete"))
    assert [(type(e), e.visit_id, e.customer_id, e.pet_id, e.outcome, e.previous_completed_at, e.occurred_at)
            for e in events.published] == [
        (VisitClosed, kong.id, 1, 101, "completed", kst(9, 2, 14), NOW),
        (VisitClosed, alone.id, 1, None, "completed", kst(9, 12, 14), NOW),
        (VisitClosed, first.id, 2, 201, "completed", None, NOW)]


async def test_완료의_VisitClosed_에는_아이의_주기와_매장의_기본_간격이_실린다():
    """⑬ — 계산한 주기는 간격 둘 이상일 때만 싣고(cycle_weeks), 직접 정한 값은 manual, 모르면 none 이다."""
    journal, visits, reports, interactor, events = _with_reports()
    interactor._settings.rows[1] = RevisitSettings(default_cycle_weeks=5)
    for month, day in ((7, 29), (8, 26)):          # 101: 이번(9/23)과 함께 4주·4주 → 계산 4주
        _completed(visits, 101, month, day)
    _completed(visits, 102, 9, 2)                  # 102: 이번과 함께 간격 하나 → single
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 16))
    momo = visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 13))
    alone = visits.seed(customer_id=1, pet_id=None, starts_at=kst(9, 23, 17))
    await interactor.transition_visits(_act([kong.id], "complete"))
    await interactor.transition_visits(_act([bori.id], "complete"))
    await interactor.transition_visits(_act([momo.id], "complete"))
    await interactor.transition_visits(_act([alone.id], "complete"))
    assert [(e.visit_id, e.cycle_weeks, e.cycle_source, e.default_cycle_weeks) for e in events.published] == [
        (kong.id, 4, "computed", 5), (bori.id, None, "single", 5), (momo.id, None, "none", 5),
        (alone.id, None, "none", 5)]


async def test_아이에게_직접_정한_주기는_manual_로_실린다():
    _, visits, _, interactor, events = _with_reports()
    interactor._directory.revisits[101] = PetRevisitFact(grooming_cycle_weeks=9, revisit_nudged_on=None)
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "complete"))
    [event] = events.published
    assert (event.cycle_weeks, event.cycle_source, event.default_cycle_weeks) == (9, "manual", 4)


async def test_가족_묶음은_같은_시작_시각끼리_pet_id_를_함께_싣고_한_마리만_취소하면_그_아이뿐이다():
    _, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
    later = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 23, 16))   # 같은 명령이지만 다른 시각
    await interactor.transition_visits(_act([kong.id, bori.id, later.id], "cancel", "shop_reason"))
    assert [(e.visit_id, e.family_pet_ids) for e in events.published] == [
        (kong.id, (101, 102)), (bori.id, (101, 102)), (later.id, (103,))]

    _, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "cancel", "shop_reason"))
    assert [(e.visit_id, e.family_pet_ids) for e in events.published] == [(kong.id, (101,))]


async def test_노쇼는_앞선_완료_없이_VisitClosed_를_발행한다():
    _, visits, interactor, events = _setup()
    _completed(visits, 101, 9, 2)
    past = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 10))
    await interactor.transition_visits(_act([past.id], "no_show"))
    [event] = events.published
    assert (type(event), event.visit_id, event.outcome, event.previous_completed_at) == (
        VisitClosed, past.id, "no_show", None)


async def test_되돌리기는_revived_인_VisitReserved_를_발행하고_시작은_발행하지_않는다():
    _, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "start"))
    assert events.published == []
    canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled", canceled_at=NOW,
                           cancel_reason="customer_request")
    await interactor.transition_visits(_act([canceled.id], "revert"))
    [event] = events.published
    assert (type(event), event.visit_id, event.starts_at, event.revived) == (
        VisitReserved, canceled.id, kst(9, 30, 14), True)


# --- ⑭ 이후 전부 취소 -------------------------------------------------------------------------------------------------

WEEKLY = (kst(10, 2, 14), kst(10, 9, 14), kst(10, 16, 14), kst(10, 23, 14))


def _weekly(visits, statuses):
    rows = {}
    for at in WEEKLY:
        for pet in (101, 102):
            status = statuses.get((at, pet), "reserved")
            extra = {}
            if status == "canceled":
                extra = dict(canceled_at=kst(9, 20), cancel_reason="customer_request")
            if status in ("in_progress", "completed"):
                extra = dict(started_at=at)
            if status == "completed":
                extra["completed_at"] = at
            rows[(at, pet)] = visits.seed(customer_id=1, pet_id=pet, starts_at=at, series_id=7, status=status, **extra)
    return rows


MIXED = {(WEEKLY[0], 101): "completed", (WEEKLY[0], 102): "completed", (WEEKLY[2], 101): "canceled",
         (WEEKLY[3], 102): "in_progress"}


async def test_이후_전부_취소는_뒤의_예약됨만_취소한다():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits, MIXED)
    anchors = [rows[(WEEKLY[1], 101)].id, rows[(WEEKLY[1], 102)].id]
    result = await interactor.transition_visits(_act(anchors, "cancel", "customer_request", scope="following"))
    canceled = {key for key, row in rows.items() if visits.rows[row.id].status == "canceled"}
    assert canceled == {(WEEKLY[1], 101), (WEEKLY[1], 102), (WEEKLY[2], 101), (WEEKLY[2], 102), (WEEKLY[3], 101)}
    assert visits.rows[rows[(WEEKLY[3], 102)].id].status == "in_progress"
    assert [visits.rows[rows[(WEEKLY[0], p)].id].status for p in (101, 102)] == ["completed", "completed"]
    assert sorted(v.visit_id for v in result.visits) == sorted(
        rows[k].id for k in ((WEEKLY[1], 101), (WEEKLY[1], 102), (WEEKLY[2], 102), (WEEKLY[3], 101)))


async def test_취소_안내는_가장_가까운_회차_한_통():
    _, visits, interactor, events = _setup()
    rows = _weekly(visits, {})
    anchors = [rows[(WEEKLY[2], 101)].id, rows[(WEEKLY[2], 102)].id]
    await interactor.transition_visits(_act(anchors, "cancel", "shop_reason", scope="following"))
    canceled = sorted((e.starts_at, e.pet_id, e.quiet, e.family_pet_ids) for e in events.published
                      if isinstance(e, VisitCanceled))
    assert canceled == [(WEEKLY[2], 101, False, (101, 102)), (WEEKLY[2], 102, False, (101, 102)),
                        (WEEKLY[3], 101, True, (101, 102)), (WEEKLY[3], 102, True, (101, 102))]


async def test_notice_에_취소한_회차가_전부():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits, {})
    result = await interactor.transition_visits(
        _act([rows[(WEEKLY[2], 101)].id], "cancel", "customer_request", scope="following", family=False))
    [part] = result.notice
    assert part.kind == "series_cancel"
    assert part.text == "[Hiss Haus] 예약을 취소했어요.\n아이101\n· 10월 16일(금) 오후 2:00\n· 10월 23일(금) 오후 2:00"
    assert visits.rows[rows[(WEEKLY[2], 102)].id].status == "reserved"


async def test_이후_전부는_취소에만():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits, {})
    with pytest.raises(VisitInputError):
        await interactor.transition_visits(_act([rows[(WEEKLY[1], 101)].id], "no_show", scope="following"))


async def test_예약됨이_아닌_회차에서_이후_전부_취소는_409():
    _, visits, interactor, _ = _setup()
    rows = _weekly(visits, {(WEEKLY[1], 101): "in_progress"})
    with pytest.raises(VisitStateConflictError):
        await interactor.transition_visits(
            _act([rows[(WEEKLY[1], 101)].id], "cancel", "customer_request", scope="following"))


async def test_전이의_scope_없는_예전_요청은_지금처럼():
    _, visits, interactor, events = _setup()
    rows = _weekly(visits, {})
    result = await interactor.transition_visits(_act([rows[(WEEKLY[1], 101)].id], "cancel", "customer_request"))
    assert [k for k, row in rows.items() if visits.rows[row.id].status == "canceled"] == [(WEEKLY[1], 101)]
    assert result.notice == []
    assert [e.quiet for e in events.published if isinstance(e, VisitCanceled)] == [False]
