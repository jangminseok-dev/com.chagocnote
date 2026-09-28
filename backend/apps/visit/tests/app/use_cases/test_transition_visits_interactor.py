from dataclasses import replace
from datetime import timedelta

import pytest

from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
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
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeReportRepository, FakeVisits, Journal

NOW = kst(9, 23, 15)


def _with_reports(visits=None):
    journal = Journal()
    visits, directory = visits or FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102, 103), passed=(103,))
    directory.family(2, pets=(201,))
    reports = FakeReportRepository(visits)
    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), reports, directory, now=lambda: NOW)
    return journal, visits, reports, interactor


def _setup():
    journal, visits, _, interactor = _with_reports()
    return journal, visits, interactor


def _act(ids, action, reason=None, member_id=11):
    return TransitionVisitsCommand(ctx=ctx(member_id=member_id), visit_ids=tuple(ids), action=action,
                                   cancel_reason=reason)


async def test_가족_묶음을_한_번에_완료하고_최근_방문을_알린다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
    result = await interactor.transition_visits(_act([kong.id, bori.id], "complete", member_id=12))
    assert [(v.status, v.status_changed_by_member_id) for v in result.visits] == [("completed", 12)] * 2
    assert visits.rows[kong.id].completed_at == NOW
    names = [entry[0] for entry in journal]
    assert names == ["lock_family", "lock_visits", "apply_changes", "set_last_visit"]
    assert journal[0] == ("lock_family", 1, ())   # 되돌리기가 아니면 보호자만 잠근다
    assert journal[-1] == ("set_last_visit", 1, kst(9, 23, 13))


async def test_완료를_되돌리면_최근_방문을_다시_계산한다():
    journal, visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    today = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13), status="completed",
                        started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))
    await interactor.transition_visits(_act([today.id], "revert"))
    assert visits.rows[today.id].status == "reserved"
    assert journal[0] == ("lock_family", 1, (101,))   # 되돌리기는 아이도 확인한다
    assert journal[-1] == ("set_last_visit", 1, kst(9, 2, 14))


async def test_완료와_상관없는_전이는_최근_방문을_건드리지_않는다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "cancel", "customer_request"))
    assert "set_last_visit" not in [entry[0] for entry in journal]
    assert (visits.rows[kong.id].status, visits.rows[kong.id].cancel_reason) == ("canceled", "customer_request")


async def test_하나라도_안_되면_아무것도_바꾸지_않는다():
    """V6 — 미용 중과 예약됨이 섞인 묶음에 '시작'을 누르면 둘 다 그대로다."""
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13), status="in_progress",
                       started_at=kst(9, 23, 13))
    with pytest.raises(VisitStateConflictError):
        await interactor.transition_visits(_act([kong.id, bori.id], "start"))
    assert (visits.rows[kong.id].status, visits.rows[bori.id].status) == ("reserved", "in_progress")
    assert "apply_changes" not in [entry[0] for entry in journal]


async def test_상태_규칙은_도메인이_정한다():
    _, visits, interactor = _setup()
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
    _, visits, interactor = _setup()
    canceled = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="shop_reason")
    with pytest.raises(FamilyPetPassedAwayError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


async def test_되돌린_자리에_이미_새_예약이_있으면_VISIT_DUPLICATE_다():
    _, visits, interactor = _setup()
    canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="customer_request")
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14))
    with pytest.raises(VisitDuplicateError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
    journal, visits, interactor = _setup()
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
                                            now=lambda: NOW)
    with pytest.raises(VisitStateConflictError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


def _done(visits, pet_id=101):
    return visits.seed(customer_id=1, pet_id=pet_id, starts_at=kst(9, 23, 13), status="completed",
                       started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))


async def _send(reports, visit_id, expires_at=NOW + timedelta(days=7)):
    """어제 보낸 링크."""
    await reports.create(ctx(), visit_id, bytes(16), expires_at, NOW - timedelta(days=1))


async def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
    journal, visits, reports, interactor = _with_reports()
    sent = _done(visits)
    await _send(reports, sent.id)
    with pytest.raises(VisitReportSentError):
        await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "completed"
    assert [entry[0] for entry in journal] == ["lock_family", "lock_visits"]


async def test_링크를_끊으면_되돌려진다():
    _, visits, reports, interactor = _with_reports()
    sent = _done(visits)
    await _send(reports, sent.id)
    await reports.revoke(ctx(), sent.id, NOW)
    await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "reserved"


async def test_링크의_기간이_지나면_되돌려진다():
    _, visits, reports, interactor = _with_reports()
    sent = _done(visits)
    await _send(reports, sent.id, expires_at=NOW)   # 지금 끝난다
    await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "reserved"


async def test_함께_되돌리는_방문_하나에_알림장이_있으면_둘_다_그대로다():
    journal, visits, reports, interactor = _with_reports()
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
    _, visits, reports, interactor = _with_reports(_SentWhileLocking())
    visits.reports = reports
    sent = _done(visits)
    with pytest.raises(VisitReportSentError):
        await interactor.transition_visits(_act([sent.id], "revert"))
    assert visits.rows[sent.id].status == "completed"
