"""반복 회차 미리 보기(⑭ 설계 3.7) — 회차마다 시각·경고·이미 예약된 자리, 1년을 넘는 회차는 빠진다. 저장하지 않는다."""
import pytest

from visit.app.dtos.preview_repeat_dto import PreviewRepeatQuery
from visit.app.use_cases.preview_repeat_interactor import PreviewRepeatInteractor
from visit.domain.errors import MenuNotAvailableError, VisitCrossesMidnightError, VisitInputError
from visit.domain.value_objects.closed_date import ClosedDate
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, FakeVisits, Journal

NOW = kst(11, 17, 10)


def _setup():
    journal = Journal()
    visits, menus, schedule = FakeVisits(journal), FakeMenus(journal), FakeSchedule(journal)
    interactor = PreviewRepeatInteractor(visits, visits, menus, schedule, now=lambda: NOW)
    return visits, menus, schedule, interactor


def _query(**change):
    fields = dict(ctx=ctx(), customer_id=1, pet_ids=(101,), starts_at=kst(11, 20, 14), duration_minutes=90,
                  menu_ids=(), interval_weeks=4, count=3)
    return PreviewRepeatQuery(**(fields | change))


async def test_회차마다_시각과_경고를_준다():
    _, _, schedule, interactor = _setup()
    day = kst(12, 18, 14).astimezone(__import__("zoneinfo").ZoneInfo("Asia/Seoul")).date()
    schedule.closed[(1, day)] = ClosedDate(day=day, note=None)
    view = await interactor.preview_repeat(_query())
    assert [(o.index, o.starts_at.isoformat(), o.warnings, o.taken) for o in view.occurrences] == [
        (1, "2026-11-20T14:00:00+09:00", [], False),
        (2, "2026-12-18T14:00:00+09:00", ["closed_day"], False),
        (3, "2027-01-15T14:00:00+09:00", [], False),
    ]
    assert (view.interval_weeks, view.count, view.beyond_horizon) == (4, 3, 0)


async def test_1년을_넘는_회차는_없고_그_수를_준다():
    _, _, _, interactor = _setup()
    view = await interactor.preview_repeat(_query(interval_weeks=12, count=6))
    assert [o.index for o in view.occurrences] == [1, 2, 3, 4, 5]
    assert view.beyond_horizon == 1


async def test_그_아이가_이미_그_시각에_예약이_있으면_taken():
    visits, _, _, interactor = _setup()
    visits.seed(pet_id=101, starts_at=kst(12, 18, 14))
    visits.seed(pet_id=102, starts_at=kst(11, 20, 14))   # 형제 — 같은 시각에 오면 가족 묶음일 뿐
    view = await interactor.preview_repeat(_query())
    assert [o.taken for o in view.occurrences] == [False, True, False]


async def test_보호자만이면_보호자의_아이_없는_예약과_겹칠_때_taken():
    visits, _, _, interactor = _setup()
    visits.seed(pet_id=None, starts_at=kst(11, 20, 14))
    view = await interactor.preview_repeat(_query(pet_ids=()))
    assert [o.taken for o in view.occurrences] == [True, False, False]


async def test_고를_수_없는_메뉴면_MENU_NOT_AVAILABLE():
    _, _, _, interactor = _setup()
    with pytest.raises(MenuNotAvailableError):
        await interactor.preview_repeat(_query(menu_ids=(999,)))


async def test_첫_시각이_범위_밖이면_VISIT_INPUT():
    _, _, _, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.preview_repeat(_query(starts_at=kst(11, 20, 14, 5)))   # 10분 단위가 아니다


async def test_자정을_넘기면_VISIT_CROSSES_MIDNIGHT():
    _, _, _, interactor = _setup()
    with pytest.raises(VisitCrossesMidnightError):
        await interactor.preview_repeat(_query(starts_at=kst(11, 20, 23), duration_minutes=120))


async def test_소요가_없으면_메뉴로_센다():
    _, menus, _, interactor = _setup()
    bath = menus.seed("목욕", minutes=60)
    view = await interactor.preview_repeat(_query(duration_minutes=None, menu_ids=(bath.id,)))
    assert len(view.occurrences) == 3
