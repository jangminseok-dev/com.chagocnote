from visit.adapter.inbound.api.v1.delete_visit_record_router import delete_visit_record_router
from visit.dependencies.delete_visit_record_provider import get_delete_visit_record_use_case
from visit.domain.errors import RecordNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


async def test_사장은_기록을_지운다_204():
    stub = Recorder(None)
    async with client(build_app(delete_visit_record_router, get_delete_visit_record_use_case, stub)) as c:
        response = await c.delete("/v1/shops/3/visits/4/record")
    assert (response.status_code, stub.calls[0].visit_id) == (204, 4)


async def test_직원은_기록을_지우지_못한다():
    """기록 삭제는 record:delete(사장만) — 시드의 권한 표를 따른다."""
    async with client(build_app(delete_visit_record_router, get_delete_visit_record_use_case, Recorder(None),
                                STAFF)) as c:
        assert error_of(await c.delete("/v1/shops/3/visits/4/record")) == (403, "PERMISSION_DENIED")


async def test_기록이_없으면_404():
    stub = Recorder(error=RecordNotFoundError("없음"))
    async with client(build_app(delete_visit_record_router, get_delete_visit_record_use_case, stub)) as c:
        assert error_of(await c.delete("/v1/shops/3/visits/4/record")) == (404, "RECORD_NOT_FOUND")
