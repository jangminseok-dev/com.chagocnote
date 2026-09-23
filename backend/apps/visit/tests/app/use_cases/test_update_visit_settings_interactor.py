from datetime import time

import pytest

from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand
from visit.app.use_cases.update_visit_settings_interactor import UpdateVisitSettingsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_수정은_검증하고_준비한_뒤_바꾼다():
    schedule = FakeSchedule()
    new = ScheduleSettings(time(9, 30), time(18), 90, frozenset({0}))
    view = await UpdateVisitSettingsInteractor(schedule).update_visit_settings(
        UpdateVisitSettingsCommand(ctx=ctx(), settings=new))
    assert (view.opens_at, view.closed_weekdays) == (time(9, 30), [0])
    assert schedule.journal == [("ensure", 1), ("update_settings", 1)]


@pytest.mark.parametrize("settings", [
    ScheduleSettings(time(19), time(10), 120, frozenset()),        # 여는 시각이 늦다
    ScheduleSettings(time(10), time(10), 120, frozenset()),        # 같다
    ScheduleSettings(time(10, 15), time(19), 120, frozenset()),    # 10분 단위가 아니다
    ScheduleSettings(time(10), time(19), 95, frozenset()),         # 소요 규칙
])
async def test_규칙에_어긋나면_쓰지_않는다(settings):
    schedule = FakeSchedule()
    with pytest.raises(VisitInputError):
        await UpdateVisitSettingsInteractor(schedule).update_visit_settings(
            UpdateVisitSettingsCommand(ctx=ctx(), settings=settings))
    assert schedule.journal == []
