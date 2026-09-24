from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.list_menus_provider import get_list_menus_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client

BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False, price=30000)


async def test_직원도_정가가_든_메뉴표를_본다():
    stub = Recorder([BATH])
    async with client(build_app(list_menus_router, get_list_menus_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/menus")
        await c.get("/v1/shops/3/menus?include_archived=true")
    assert response.json() == {"items": [{"menu_id": 1, "name": "목욕", "default_duration_minutes": 60,
                                          "sort_order": 1, "archived": False, "price": 30000}]}
    assert [q.include_archived for q in stub.calls] == [False, True]
