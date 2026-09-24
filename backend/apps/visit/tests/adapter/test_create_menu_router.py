from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.create_menu_provider import get_create_menu_use_case
from visit.domain.errors import MenuNameTakenError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

NAIL = MenuView(menu_id=6, name="발톱", default_duration_minutes=None, sort_order=6, archived=False, price=None)


async def test_사장은_메뉴를_만든다_201():
    stub = Recorder(NAIL)
    async with client(build_app(create_menu_router, get_create_menu_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/menus", json={"name": " 발톱 "})
    assert (response.status_code, response.json()["menu_id"]) == (201, 6)
    assert (stub.calls[0].name, stub.calls[0].default_duration_minutes, stub.calls[0].price) == ("발톱", None, None)


async def test_직원은_메뉴를_만들지_못한다():
    async with client(build_app(create_menu_router, get_create_menu_use_case, Recorder(NAIL), STAFF)) as c:
        response = await c.post("/v1/shops/3/menus", json={"name": "발톱"})
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_이름이_비었거나_길거나_소요가_문자열이면_422_다():
    async with client(build_app(create_menu_router, get_create_menu_use_case, Recorder(NAIL))) as c:
        for bad in ({"name": " "}, {"name": "가" * 31}, {"name": "발톱", "default_duration_minutes": "60"},
                    {"name": "발\x00톱"}, {"name": "발톱", "price": -1}, {"name": "발톱", "price": 100_000_001}):
            assert error_of(await c.post("/v1/shops/3/menus", json=bad)) == (422, "VALIDATION_ERROR")


async def test_이름이_겹치면_409_MENU_NAME_TAKEN_이다():
    stub = Recorder(error=MenuNameTakenError("겹침"))
    async with client(build_app(create_menu_router, get_create_menu_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/menus", json={"name": "목욕"})
    assert error_of(response) == (409, "MENU_NAME_TAKEN")
