import pytest

from visit.app.dtos.get_visit_dto import GetVisitQuery
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.domain.errors import VisitNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits


def _setup():
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    return visits, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory)


async def test_묶음_지난_방문_노쇼_횟수를_함께_준다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(8, 1, 14), status="completed",
                started_at=kst(8, 1, 14), completed_at=kst(8, 1, 15))
    last = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                       started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 10, 14), status="completed",
                started_at=kst(9, 10, 14), completed_at=kst(9, 10, 15))   # 형제의 방문은 지난 방문이 아니다
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 16, 14), status="no_show")
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert detail.visit.visit_id == kong.id
    assert [v.visit_id for v in detail.group] == [bori.id]
    assert (detail.previous_visit.visit_id, detail.previous_visit.starts_at.isoformat()) == (
        last.id, "2026-09-02T14:00:00+09:00")
    assert detail.no_show_count == 1


async def test_지난_방문이_없으면_비어_있다():
    visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert (detail.group, detail.previous_visit, detail.no_show_count) == ([], None, 0)


async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    visits, interactor = _setup()
    theirs = visits.seed(shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.get_visit(GetVisitQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))
