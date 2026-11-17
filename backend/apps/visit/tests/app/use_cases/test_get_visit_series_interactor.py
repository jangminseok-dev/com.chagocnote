"""반복 묶음의 예약 목록(⑭) — 상태와 상관없이 시각 순. 다른 매장의 묶음은 없다."""
import pytest

from visit.app.dtos.get_visit_series_dto import GetVisitSeriesQuery
from visit.app.use_cases.get_visit_series_interactor import GetVisitSeriesInteractor
from visit.domain.errors import VisitSeriesNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSeries, FakeVisits


def _setup():
    visits, series, directory = FakeVisits(), FakeSeries(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    series.seed(7, interval_weeks=2)
    return visits, series, GetVisitSeriesInteractor(visits, series, directory, FakeMenus())


async def test_묶음의_방문을_상태와_상관없이_시각순으로():
    visits, _, interactor = _setup()
    late = visits.seed(pet_id=101, starts_at=kst(12, 4, 14), series_id=7)
    done = visits.seed(pet_id=101, starts_at=kst(11, 20, 14), series_id=7, status="completed",
                       started_at=kst(11, 20, 14), completed_at=kst(11, 20, 15))
    visits.seed(pet_id=101, starts_at=kst(11, 27, 14))   # 묶음 밖
    view = await interactor.get_visit_series(GetVisitSeriesQuery(ctx=ctx(), series_id=7))
    assert (view.id, view.interval_weeks) == (7, 2)
    assert [(v.visit_id, v.status) for v in view.visits] == [(done.id, "completed"), (late.id, "reserved")]


async def test_다른_매장의_묶음은_404():
    _, _, interactor = _setup()
    with pytest.raises(VisitSeriesNotFoundError):
        await interactor.get_visit_series(GetVisitSeriesQuery(ctx=ctx(shop_id=2), series_id=7))
