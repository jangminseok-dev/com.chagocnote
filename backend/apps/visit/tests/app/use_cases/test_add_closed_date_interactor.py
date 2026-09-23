from datetime import date

from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.use_cases.add_closed_date_interactor import AddClosedDateInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_추가는_설정을_준비한_뒤_넣는다():
    schedule = FakeSchedule()
    view = await AddClosedDateInteractor(schedule).add_closed_date(
        AddClosedDateCommand(ctx=ctx(), day=date(2026, 10, 9), note="한글날"))
    assert (view.date, view.note) == (date(2026, 10, 9), "한글날")
    assert schedule.journal == [("ensure", 1), ("add_closed_date", date(2026, 10, 9))]
