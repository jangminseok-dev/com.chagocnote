from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView
from visit.dependencies.transition_visits_provider import get_transition_visits_use_case
from visit.domain.errors import VisitNotYetError, VisitStateConflictError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

DONE = TransitionedVisitsView(visits=[visit_view(status="completed")])


async def _post(body, stub=None, access=STAFF):
    stub = stub or Recorder(DONE)
    async with client(build_app(transition_visits_router, get_transition_visits_use_case, stub, access)) as c:
        return await c.post("/v1/shops/3/visits/transitions", json=body), stub


async def test_직원도_상태를_바꾼다():
    response, stub = await _post({"visit_ids": [1, 2], "action": "cancel", "cancel_reason": "shop_reason"})
    assert response.json()["visits"][0]["status"] == "completed"
    command = stub.calls[0]
    assert (command.visit_ids, command.action, command.cancel_reason) == ((1, 2), "cancel", "shop_reason")


async def test_모르는_행동과_사유_빈_목록은_422_다():
    for bad in ({"visit_ids": [1], "action": "teleport"},
                {"visit_ids": [1], "action": "cancel", "cancel_reason": "weather"},
                {"visit_ids": [], "action": "start"},
                {"visit_ids": [1, 1], "action": "start"}):
        response, _ = await _post(bad)
        assert error_of(response) == (422, "VALIDATION_ERROR"), bad


async def test_권한과_상태_오류():
    response, _ = await _post({"visit_ids": [1], "action": "start"}, access=READ_ONLY)
    assert error_of(response) == (403, "PERMISSION_DENIED")
    for error, expected in ((VisitStateConflictError("충돌"), (409, "VISIT_STATE_CONFLICT")),
                            (VisitNotYetError("아직"), (409, "VISIT_NOT_YET"))):
        response, _ = await _post({"visit_ids": [1], "action": "start"}, stub=Recorder(error=error))
        assert error_of(response) == expected
