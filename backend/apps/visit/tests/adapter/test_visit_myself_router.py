from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
from visit.app.dtos.visit_myself_dto import VisitMyselfResponse
from visit.dependencies.visit_myself_provider import get_visit_myself_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_멤버는_자기소개를_본다():
    stub = Recorder(VisitMyselfResponse(id=5, name="방문 (visit)", introduction="소개"))
    async with client(build_app(visit_myself_router, get_visit_myself_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/myself")
    assert response.json() == {"id": 5, "name": "방문 (visit)", "introduction": "소개"}
