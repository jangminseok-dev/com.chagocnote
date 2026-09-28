import pytest

from visit.adapter.inbound.api.v1.mark_report_viewed_router import mark_report_viewed_router
from visit.dependencies.mark_report_viewed_provider import get_mark_report_viewed_use_case
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import make_token
from visit.tests.helpers.api import Recorder, build_app, client, error_of

TOKEN = make_token(bytes(range(16)), bytes(range(32)))


async def _post(stub, headers=None):
    async with client(build_app(mark_report_viewed_router, get_mark_report_viewed_use_case, stub)) as c:
        return await c.post("/v1/public/report/viewed", headers=headers)


async def test_열람_신호는_본문_없이_204_다():
    stub = Recorder()
    response = await _post(stub, {"X-Report-Token": TOKEN})
    assert (response.status_code, response.content) == (204, b"")
    assert response.headers["cache-control"] == "private, no-store"
    assert (stub.calls[0].token, stub.calls[0].client) == (TOKEN, "127.0.0.1")


@pytest.mark.parametrize("headers", [
    None, {"X-Report-Token": ""}, {"X-Report-Token": "a" * 5000}, {"X-Report-Token": "알림장".encode()},
], ids=["헤더 없음", "빈 값", "5000글자", "한글"])
async def test_이상한_토큰은_422_가_아니라_404_다(headers):
    """R13"""
    stub = Recorder(error=ReportNotFoundError("알림장을 찾을 수 없습니다."))
    assert error_of(await _post(stub, headers)) == (404, "REPORT_NOT_FOUND")
    assert len(stub.calls) == 1


async def test_닫힌_알림장은_410_너무_잦으면_429_다():
    assert error_of(await _post(Recorder(error=ReportClosedError("닫힘")), {"X-Report-Token": TOKEN})) == (
        410, "REPORT_CLOSED")
    assert error_of(await _post(Recorder(error=TooManyReportRequestsError("잦음")), {"X-Report-Token": TOKEN})) == (
        429, "TOO_MANY_ATTEMPTS")
