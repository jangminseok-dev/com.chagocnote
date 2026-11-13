from datetime import date

from visit.adapter.inbound.api.v1.list_due_pets_router import list_due_pets_router
from visit.app.dtos.list_due_pets_dto import DuePetItemView, DuePetsView
from visit.app.services.pet_cards import PetCard
from visit.dependencies.list_due_pets_provider import get_list_due_pets_use_case
from visit.domain.errors import VisitInputError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

VIEW = DuePetsView(
    items=[DuePetItemView(pet=PetCard(101, "두부", None), last_visit_date=date(2026, 8, 1))], next_cursor="abc")
BASE = "/v1/shops/3/sales/due-pets"


def _app(stub, access=None):
    return build_app(list_due_pets_router, get_list_due_pets_use_case, stub, access)


async def test_사장은_다시_올_때가_지난_아이를_읽는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.get(BASE)
        await c.get(f"{BASE}?cursor=abc")
    assert (response.status_code, response.json()) == (200, {
        "items": [{"pet": {"pet_id": 101, "name": "두부", "photo_url": None}, "last_visit_date": "2026-08-01"}],
        "next_cursor": "abc",
    })
    assert [(q.ctx.shop_id, q.cursor) for q in stub.calls] == [(3, None), (3, "abc")]


async def test_직원은_보지_못한다():
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.get(BASE)
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


async def test_긴_쪽_표시와_깨진_쪽_표시는_422_다():
    async with client(_app(Recorder(VIEW))) as c:
        too_long = await c.get(f"{BASE}?cursor={'a' * 201}")
    assert error_of(too_long) == (422, "VALIDATION_ERROR")
    async with client(_app(Recorder(error=VisitInputError("목록을 이어서 불러올 수 없습니다.")))) as c:
        broken = await c.get(f"{BASE}?cursor=!!!!")
    assert error_of(broken) == (422, "VALIDATION_ERROR")
