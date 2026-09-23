from datetime import time

from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery
from visit.app.use_cases.get_visit_defaults_interactor import GetVisitDefaultsInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, FakeVisits


def _setup():
    visits, menus = FakeVisits(), FakeMenus()
    schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 90, frozenset()))
    return visits, menus, GetVisitDefaultsInteractor(visits, menus, schedule)


def _done(visits, **fields):
    starts = fields.pop("starts_at")
    return visits.seed(status="completed", starts_at=starts, started_at=starts, completed_at=starts, **fields)


async def test_지난_완료_방문의_메뉴와_소요로_채운다():
    visits, menus, interactor = _setup()
    bath, trim, old = menus.seed("목욕"), menus.seed("전체 미용"), menus.seed("옛 메뉴", archived=True)
    _done(visits, pet_id=101, starts_at=kst(8, 1, 14), duration_minutes=60, menu_ids=(bath.id,))
    last = _done(visits, pet_id=101, starts_at=kst(9, 2, 14), duration_minutes=150,
                 menu_ids=(trim.id, old.id))
    visits.seed(pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=30)   # 아직 오지 않은 예약은 아니다
    view = await interactor.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx(), pet_id=101))
    assert (view.source_visit_id, view.duration_minutes, [m.name for m in view.menus]) == (
        last.id, 150, ["전체 미용"])   # 보관한 메뉴는 뺀다


async def test_처음_온_아이는_빈_메뉴와_매장_기본_소요():
    _, _, interactor = _setup()
    view = await interactor.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx(), pet_id=101))
    assert (view.source_visit_id, view.duration_minutes, view.menus) == (None, 90, [])


async def test_다른_매장의_방문은_보지_않는다():
    visits, _, interactor = _setup()
    _done(visits, pet_id=101, starts_at=kst(9, 2, 14), shop_id=2)
    view = await interactor.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx(shop_id=1), pet_id=101))
    assert view.source_visit_id is None
