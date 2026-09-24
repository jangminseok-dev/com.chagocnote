import pytest

from hub.app.errors import FamilyPetNotFoundError
from visit.app.dtos.update_visit_dto import UpdateVisitCommand
from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
from visit.domain.errors import (
    MenuNotAvailableError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitNotFoundError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeMenus,
    FakeSchedule,
    FakeVisits,
    Journal,
)

NOW = kst(9, 23, 15)


def _setup():
    journal = Journal()
    visits, menus, directory = FakeVisits(journal), FakeMenus(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102, 103), passed=(103,))
    directory.family(2, pets=(201,))
    interactor = UpdateVisitInteractor(visits, menus, FakeSchedule(), directory, now=lambda: NOW)
    return journal, visits, menus, interactor


def _command(visit, **overrides):
    fields = dict(ctx=ctx(), visit_id=visit.id, starts_at=visit.starts_at, pet_id=visit.pet_id,
                  duration_minutes=visit.duration_minutes, menu_ids=visit.menu_ids, memo=visit.memo)
    fields.update(overrides)
    return UpdateVisitCommand(**fields)


async def test_예약은_시간과_아이와_메뉴를_바꾼다():
    journal, visits, menus, interactor = _setup()
    bath = menus.seed("목욕")
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    result = await interactor.update_visit(_command(
        kong, starts_at=kst(10, 3, 11), pet_id=102, duration_minutes=60, menu_ids=(bath.id,), memo="발톱"))
    row = visits.rows[kong.id]
    assert (row.starts_at, row.pet_id, row.duration_minutes, row.menu_ids, row.memo) == (
        kst(10, 3, 11), 102, 60, (bath.id,), "발톱")
    assert result.warnings == []
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("lock_visits") < names.index("update_visit")
    assert ("lock_family", 1, (102,)) in journal   # 새로 고른 아이만 확인한다


async def test_다른_보호자의_아이로는_바꾸지_못한다():
    """V13 — 반려동물은 같은 보호자의 아이로만. 가족 확인이 거절한다."""
    journal, visits, _, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    with pytest.raises(FamilyPetNotFoundError):
        await interactor.update_visit(_command(kong, pet_id=201))
    assert "update_visit" not in [entry[0] for entry in journal]


async def test_완료한_방문은_메모와_메뉴만_고친다():
    _, visits, menus, interactor = _setup()
    bath = menus.seed("목욕")
    done = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 2, 14), status="completed",
                       started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))   # 그 뒤 무지개다리를 건넌 아이
    result = await interactor.update_visit(_command(done, menu_ids=(bath.id,), memo="귀 청소도 함"))
    assert (result.visit.memo, result.warnings) == ("귀 청소도 함", [])
    for moved in (dict(starts_at=kst(9, 2, 15)), dict(pet_id=101)):
        with pytest.raises(VisitStateConflictError):
            await interactor.update_visit(_command(done, **moved))


async def test_이미_붙은_메뉴는_보관됐어도_둘_수_있다():
    _, visits, menus, interactor = _setup()
    old = menus.seed("옛 메뉴", archived=True)
    other_old = menus.seed("다른 옛 메뉴", archived=True)
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), menu_ids=(old.id,))
    await interactor.update_visit(_command(kong, memo="그대로"))
    with pytest.raises(MenuNotAvailableError):
        await interactor.update_visit(_command(kong, menu_ids=(old.id, other_old.id)))


async def test_시각_규칙과_중복():
    _, visits, _, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 9, 14))
    with pytest.raises(VisitCrossesMidnightError):
        await interactor.update_visit(_command(kong, starts_at=kst(10, 2, 23), duration_minutes=120))
    with pytest.raises(VisitDuplicateError):
        await interactor.update_visit(_command(kong, starts_at=kst(10, 9, 14)))


async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    _, visits, _, interactor = _setup()
    theirs = visits.seed(shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.update_visit(_command(theirs))


async def test_경고를_함께_돌려준다():
    _, visits, _, interactor = _setup()
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 11))
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    result = await interactor.update_visit(_command(kong, starts_at=kst(10, 2, 11)))
    assert result.warnings == ["overlap"]
