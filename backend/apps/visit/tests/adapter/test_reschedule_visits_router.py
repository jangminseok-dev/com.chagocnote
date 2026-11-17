from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
from visit.app.dtos.build_send_bundle_dto import BundlePartView
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView
from visit.dependencies.reschedule_visits_provider import get_reschedule_visits_use_case
from visit.domain.errors import VisitGroupMismatchError, VisitSeriesConflictError
from visit.domain.services.visit_series import TAKEN, SeriesConflict
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.builders import TZ, kst
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


async def test_이후_전부_칸_셋을_명령으로_옮기고_없으면_이_예약만():
    stub = Recorder(RescheduledVisitsView(visits=[visit_view(1)], warnings=[], notice=[
        BundlePartView(kind="series_change", text="[Hiss Haus] 예약 날짜를 바꿨어요.")]))
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visits/reschedule", json={
            **BODY, "scope": "following", "family": False, "skip_visit_ids": [7, 8]})
        assert response.json()["notice"] == [{"kind": "series_change", "text": "[Hiss Haus] 예약 날짜를 바꿨어요."}]
        await c.post("/v1/shops/3/visits/reschedule", json=BODY)
    following, plain = stub.calls
    assert (following.scope, following.family, following.skip_visit_ids) == ("following", False, (7, 8))
    assert (plain.scope, plain.family, plain.skip_visit_ids) == ("this", True, ())


async def test_모르는_scope_와_겹친_skip_은_422_걸린_회차는_409_details():
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, Recorder())) as c:
        for bad in ({**BODY, "scope": "all"}, {**BODY, "skip_visit_ids": [3, 3]}, {**BODY, "family": "yes"}):
            assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=bad)) == (422, "VALIDATION_ERROR")
    stub = Recorder(error=VisitSeriesConflictError([SeriesConflict(9, 101, kst(10, 17, 15), TAKEN)], TZ))
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/visits/reschedule", json={**BODY, "scope": "following"})
    assert response.status_code == 409
    assert response.json() == {"code": "VISIT_SERIES_CONFLICT", "message": "이미 예약이 있거나 잡을 수 없는 회차가 있어요.",
                               "details": {"conflicts": [{"visit_id": 9, "pet_id": 101,
                                                          "starts_at": "2026-10-17T15:00:00+09:00", "reason": "taken"}]}}
