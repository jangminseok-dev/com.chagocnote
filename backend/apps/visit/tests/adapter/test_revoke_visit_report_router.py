import pytest

from visit.adapter.inbound.api.v1.revoke_visit_report_router import revoke_visit_report_router
from visit.dependencies.revoke_visit_report_provider import get_revoke_visit_report_use_case
from visit.domain.errors import ReportNotFoundError, VisitNotFoundError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of


async def _delete(stub, path="/v1/shops/3/visits/4/report", access=None):
    async with client(build_app(revoke_visit_report_router, get_revoke_visit_report_use_case, stub, access)) as c:
        return await c.delete(path)


async def test_직원은_알림장_링크를_끊는다_204():
    stub = Recorder(None)
    response = await _delete(stub, access=STAFF)
    assert (response.status_code, response.content) == (204, b"")
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].visit_id) == (3, 4)


async def test_기록_권한이_없으면_끊지_못한다():
    stub = Recorder(None)
    assert error_of(await _delete(stub, access=READ_ONLY)) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


async def test_살아_있는_링크가_없으면_404_없는_방문도_404_다():
    assert error_of(await _delete(Recorder(error=ReportNotFoundError("없음")))) == (404, "REPORT_NOT_FOUND")
    assert error_of(await _delete(Recorder(error=VisitNotFoundError("없음")))) == (404, "VISIT_NOT_FOUND")


@pytest.mark.parametrize("visit_id", ["9223372036854775808", "0", "-1", "1.5", "abc", "1" * 400])
async def test_방문_ID_가_범위_밖이거나_숫자가_아니면_422_다(visit_id):
    stub = Recorder(None)
    assert error_of(await _delete(stub, f"/v1/shops/3/visits/{visit_id}/report")) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
