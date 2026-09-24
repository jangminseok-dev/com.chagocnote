from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.archive_menu_provider import get_archive_menu_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

ARCHIVED = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=True, price=None)


async def test_사장은_메뉴를_보관한다():
    stub = Recorder(ARCHIVED)
    async with client(build_app(archive_menu_router, get_archive_menu_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/menus/1/archive")
    assert response.json()["archived"] is True
    assert stub.calls[0].menu_id == 1


async def test_직원은_메뉴를_보관하지_못한다():
    async with client(build_app(archive_menu_router, get_archive_menu_use_case, Recorder(ARCHIVED), STAFF)) as c:
        assert error_of(await c.post("/v1/shops/3/menus/1/archive")) == (403, "PERMISSION_DENIED")
