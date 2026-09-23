from datetime import datetime, timezone

from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
from visit.app.dtos.update_visit_dto import UpdatedVisitView
from visit.dependencies.update_visit_provider import get_update_visit_use_case
from visit.domain.errors import VisitStateConflictError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

BODY = {"starts_at": "2026-10-03T11:00:00+09:00", "pet_id": None, "duration_minutes": 60, "menu_ids": [],
        "memo": ""}


async def test_직원도_방문을_고친다():
    stub = Recorder(UpdatedVisitView(visit=visit_view(), warnings=[]))
    async with client(build_app(update_visit_router, get_update_visit_use_case, stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/visits/1", json=BODY)
    assert response.status_code == 200
    command = stub.calls[0]
    assert (command.visit_id, command.pet_id, command.memo, command.starts_at) == (
        1, None, None, datetime(2026, 10, 3, 2, tzinfo=timezone.utc))


async def test_PUT_은_모든_칸을_받는다():
    async with client(build_app(update_visit_router, get_update_visit_use_case, Recorder())) as c:
        for key in BODY:
            partial = {k: v for k, v in BODY.items() if k != key}
            assert error_of(await c.put("/v1/shops/3/visits/1", json=partial)) == (422, "VALIDATION_ERROR"), key


async def test_권한과_상태_충돌():
    async with client(build_app(update_visit_router, get_update_visit_use_case, Recorder(), READ_ONLY)) as c:
        assert error_of(await c.put("/v1/shops/3/visits/1", json=BODY)) == (403, "PERMISSION_DENIED")
    stub = Recorder(error=VisitStateConflictError("완료"))
    async with client(build_app(update_visit_router, get_update_visit_use_case, stub)) as c:
        assert error_of(await c.put("/v1/shops/3/visits/1", json=BODY)) == (409, "VISIT_STATE_CONFLICT")
