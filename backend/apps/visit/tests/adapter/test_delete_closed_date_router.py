from datetime import date

from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
from visit.dependencies.delete_closed_date_provider import get_delete_closed_date_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


async def test_휴무_삭제는_사장만_204():
    stub = Recorder()
    async with client(build_app(delete_closed_date_router, get_delete_closed_date_use_case, stub)) as c:
        assert (await c.delete("/v1/shops/3/closed-dates/2026-10-09")).status_code == 204
        assert error_of(await c.delete("/v1/shops/3/closed-dates/10월9일")) == (422, "VALIDATION_ERROR")
    assert stub.calls[0].day == date(2026, 10, 9)
    async with client(build_app(delete_closed_date_router, get_delete_closed_date_use_case, stub, STAFF)) as c:
        assert error_of(await c.delete("/v1/shops/3/closed-dates/2026-10-09")) == (403, "PERMISSION_DENIED")
