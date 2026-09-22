from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.list_pet_condition_types_router import (
    list_pet_condition_types_router,
)
from customer.app.dtos.list_pet_condition_types_dto import ConditionTypeView
from customer.dependencies.list_pet_condition_types_provider import (
    get_list_pet_condition_types_use_case,
)
from customer.tests.helpers.api import NO_WRITE, build_app


class _StubUseCase:
    async def list_pet_condition_types(self, query):
        return [ConditionTypeView(code="patella_luxation", label="슬개골 탈구", sort_order=1)]


async def test_멤버는_질병_종류를_본다():
    app = build_app(list_pet_condition_types_router, get_list_pet_condition_types_use_case,
                    _StubUseCase(), access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/shops/3/pet-condition-types")
    assert response.json() == [{"code": "patella_luxation", "label": "슬개골 탈구", "sort_order": 1}]
