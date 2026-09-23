from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
from visit.app.dtos.register_visit_dto import RegisteredVisitsView
from visit.dependencies.register_visit_provider import get_register_visit_use_case
from visit.domain.errors import (
    MenuNotAvailableError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
)
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

BODY = {"customer_id": 1, "pet_ids": [101, 102], "starts_at": "2026-10-02T14:00:00+09:00",
        "menu_ids": [1], "memo": " 발톱 짧게 "}
CREATED = RegisteredVisitsView(visits=[visit_view()], warnings=["overlap"])


async def _post(body, stub=None, access=STAFF):
    stub = stub or Recorder(CREATED)
    async with client(build_app(register_visit_router, get_register_visit_use_case, stub, access)) as c:
        return await c.post("/v1/shops/3/visits", json=body), stub


async def test_직원도_예약을_잡고_201_로_방문과_경고를_받는다():
    response, stub = await _post(BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["warnings"] == ["overlap"]
    [visit] = body["visits"]
    assert (visit["starts_at"], visit["pet"]["weight_kg"], visit["menus"]) == (
        "2026-10-02T14:00:00+09:00", 3.2, [{"menu_id": 1, "name": "목욕"}])
    command = stub.calls[0]
    assert (command.ctx.shop_id, command.pet_ids, command.menu_ids, command.memo, command.walk_in) == (
        3, (101, 102), (1,), "발톱 짧게", False)


async def test_지금_시작은_시각_없이_보낸다():
    response, stub = await _post({"customer_id": 1, "walk_in": True})
    assert response.status_code == 201
    assert (stub.calls[0].starts_at, stub.calls[0].walk_in, stub.calls[0].pet_ids) == (None, True, ())


async def test_reservation_write_가_없으면_403_이다():
    response, _ = await _post(BODY, access=READ_ONLY)
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_형식이_틀리면_422_VALIDATION_ERROR_다():
    for bad in (
        {**BODY, "starts_at": "2026-10-02T14:00:00"},       # 시간대 없는 시각
        {**BODY, "pet_ids": [101, 101]},                    # 같은 아이 두 번
        {**BODY, "menu_ids": [1, 1]},
        {**BODY, "customer_id": "1"},
        {**BODY, "memo": "발\x00톱"},
        {**BODY, "pet_ids": list(range(1, 12))},            # 열한 마리
        {**BODY, "walk_in": "true"},
    ):
        response, _ = await _post(bad)
        assert error_of(response) == (422, "VALIDATION_ERROR"), bad


async def test_도메인_오류는_설계의_코드와_상태다():
    for error, expected in (
        (VisitDuplicateError("중복"), (409, "VISIT_DUPLICATE")),
        (VisitCrossesMidnightError("자정"), (422, "VISIT_CROSSES_MIDNIGHT")),
        (MenuNotAvailableError("메뉴"), (422, "MENU_NOT_FOUND")),
    ):
        response, _ = await _post(BODY, stub=Recorder(error=error))
        assert error_of(response) == expected
