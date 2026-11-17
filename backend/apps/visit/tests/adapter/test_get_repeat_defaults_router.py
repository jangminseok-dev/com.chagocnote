from visit.adapter.inbound.api.v1.get_repeat_defaults_router import get_repeat_defaults_router
from visit.app.dtos.get_repeat_defaults_dto import RepeatDefaultsView
from visit.dependencies.get_repeat_defaults_provider import get_get_repeat_defaults_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_repeat_defaults_는_멤버가_읽고_칸을_고정한다():
    stub = Recorder(RepeatDefaultsView(5, "cycle", 101, 5, 6))
    app = build_app(get_repeat_defaults_router, get_get_repeat_defaults_use_case, stub, STAFF)
    async with client(app) as c:
        response = await c.get("/v1/shops/3/visits/repeat-defaults?customer_id=7&pet_ids=101&pet_ids=102")
    assert response.status_code == 200
    assert response.json() == {"interval_weeks": 5, "source": "cycle", "pet_id": 101, "cycle_weeks": 5, "count": 6}
    query = stub.calls[0]
    assert (query.ctx.shop_id, query.customer_id, query.pet_ids) == (3, 7, (101, 102))


async def test_repeat_defaults_의_잘못된_쿼리는_422():
    app = build_app(get_repeat_defaults_router, get_get_repeat_defaults_use_case, Recorder(), STAFF)
    async with client(app) as c:
        for query in ("", "customer_id=0", "customer_id=7&pet_ids=abc"):
            assert (await c.get(f"/v1/shops/3/visits/repeat-defaults?{query}")).status_code == 422
