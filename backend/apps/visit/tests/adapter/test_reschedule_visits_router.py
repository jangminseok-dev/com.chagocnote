from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView
from visit.dependencies.reschedule_visits_provider import get_reschedule_visits_use_case
from visit.domain.errors import VisitGroupMismatchError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

BODY = {"visit_ids": [1, 2], "starts_at": "2026-10-03T15:00:00+09:00"}


async def test_직원도_가족_예약을_함께_옮긴다():
    stub = Recorder(RescheduledVisitsView(visits=[visit_view(1), visit_view(2)], warnings=["overlap"]))
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visits/reschedule", json=BODY)
    assert (len(response.json()["visits"]), response.json()["warnings"]) == (2, ["overlap"])
    assert stub.calls[0].visit_ids == (1, 2)


async def test_형식_권한_묶음_오류():
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, Recorder())) as c:
        for bad in ({**BODY, "visit_ids": []}, {**BODY, "visit_ids": [1, 1]}, {**BODY, "starts_at": "2026-10-03T15:00"}):
            assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=bad)) == (422, "VALIDATION_ERROR")
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, Recorder(), READ_ONLY)) as c:
        assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=BODY)) == (403, "PERMISSION_DENIED")
    stub = Recorder(error=VisitGroupMismatchError("섞임"))
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, stub)) as c:
        assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=BODY)) == (422, "VISIT_GROUP_MISMATCH")
