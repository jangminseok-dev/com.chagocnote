from datetime import date

import pytest

from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.use_cases.list_closed_dates_interactor import ListClosedDatesInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.closed_date import ClosedDate
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_기간_안의_휴무를_날짜_순으로():
    schedule = FakeSchedule()
    for shop, day in ((1, date(2026, 10, 9)), (1, date(2026, 10, 3)), (1, date(2026, 11, 1)), (2, date(2026, 10, 5))):
        schedule.closed[(shop, day)] = ClosedDate(day=day, note=None)
    views = await ListClosedDatesInteractor(schedule).list_closed_dates(
        ListClosedDatesQuery(ctx=ctx(), start=date(2026, 10, 1), end=date(2026, 10, 31)))
    assert [v.date for v in views] == [date(2026, 10, 3), date(2026, 10, 9)]


@pytest.mark.parametrize(("start", "end"), [
    (date(2026, 10, 2), date(2026, 10, 1)),     # 거꾸로
    (date(2026, 1, 1), date(2027, 2, 6)),       # 401일
])
async def test_기간이_거꾸로거나_400일을_넘으면_VALIDATION_ERROR_다(start, end):
    with pytest.raises(VisitInputError):
        await ListClosedDatesInteractor(FakeSchedule()).list_closed_dates(
            ListClosedDatesQuery(ctx=ctx(), start=start, end=end))
