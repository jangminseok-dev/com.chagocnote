from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.list_members_router import list_members_router
from tenancy.app.dtos.list_members_dto import MemberView
from tenancy.dependencies.list_members_provider import get_list_members_use_case
from tenancy.tests.helpers.api import STAFF_PERMISSIONS, StubShopAccess, build_app

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def list_members(self, query):
        self.queries.append(query)
        return [MemberView(member_id=11, user_id=1, display_name="사장님",
                           profile_image_url=None, role="owner", joined_at=JOINED)]


async def _get(stub, access, user_id=5):
    app = build_app(list_members_router, get_list_members_use_case, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/shops/3/members")


async def test_직원도_멤버_목록을_본다():
    stub = _StubUseCase()
    response = await _get(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert response.status_code == 200
    assert response.json() == [{
        "member_id": 11, "user_id": 1, "display_name": "사장님", "profile_image_url": None,
        "role": "owner", "joined_at": "2026-09-20T12:00:00Z",
    }]
    assert stub.queries[0].ctx.shop_id == 3


async def test_토큰이_없으면_401_이다():
    response = await _get(_StubUseCase(), StubShopAccess(), user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
