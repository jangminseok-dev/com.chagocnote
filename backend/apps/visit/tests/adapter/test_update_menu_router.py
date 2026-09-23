from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.update_menu_provider import get_update_menu_use_case
from visit.domain.errors import MenuNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False)
BODY = {"name": "목욕", "default_duration_minutes": 60, "sort_order": 2}


async def test_사장은_메뉴를_고친다():
    stub = Recorder(BATH)
    async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
        assert (await c.put("/v1/shops/3/menus/1", json=BODY)).status_code == 200
    assert (stub.calls[0].menu_id, stub.calls[0].sort_order) == (1, 2)


async def test_직원은_메뉴를_고치지_못한다():
    async with client(build_app(update_menu_router, get_update_menu_use_case, Recorder(BATH), STAFF)) as c:
        assert error_of(await c.put("/v1/shops/3/menus/1", json=BODY)) == (403, "PERMISSION_DENIED")


async def test_순서값이_상한을_넘으면_422_다():
    stub = Recorder(BATH)
    async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
        body = {**BODY, "sort_order": 10000}
        assert error_of(await c.put("/v1/shops/3/menus/1", json=body)) == (422, "VALIDATION_ERROR")


async def test_없는_메뉴는_404_범위를_넘는_ID_는_422_다():
    stub = Recorder(error=MenuNotFoundError("없음"))
    async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
        assert error_of(await c.put("/v1/shops/3/menus/9", json=BODY)) == (404, "MENU_NOT_FOUND")
        assert error_of(await c.put("/v1/shops/3/menus/9223372036854775808", json=BODY)) == (
            422, "VALIDATION_ERROR")
