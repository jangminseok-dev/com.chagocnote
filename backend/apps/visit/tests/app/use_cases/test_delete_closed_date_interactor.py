from datetime import date

from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand
from visit.app.use_cases.delete_closed_date_interactor import DeleteClosedDateInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_삭제는_없어도_성공한다():
    schedule = FakeSchedule()
    await DeleteClosedDateInteractor(schedule).delete_closed_date(
        DeleteClosedDateCommand(ctx=ctx(), day=date(2026, 10, 9)))
    assert schedule.journal == [("delete_closed_date", date(2026, 10, 9))]
