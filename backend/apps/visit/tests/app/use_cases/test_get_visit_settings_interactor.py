from datetime import time

from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.use_cases.get_visit_settings_interactor import GetVisitSettingsInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_조회는_설정을_준비하고_쉬는_요일을_정렬해_돌려준다():
    schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 120, frozenset({6, 0})))
    view = await GetVisitSettingsInteractor(schedule).get_visit_settings(GetVisitSettingsQuery(ctx=ctx()))
    assert (view.opens_at, view.closes_at, view.default_duration_minutes, view.closed_weekdays) == (
        time(10), time(19), 120, [0, 6])
    assert schedule.journal == [("ensure", 1)]
