from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.change_member_role_router import change_member_role_router
from tenancy.app.dtos.change_member_role_dto import ChangedMember
from tenancy.dependencies.change_member_role_provider import get_change_member_role_use_case
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def change_role(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return ChangedMember(member_id=command.member_id, user_id=2, role=command.role)


async def _patch(stub, access, body):
    app = build_app(change_member_role_router, get_change_member_role_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.patch("/v1/shops/3/members/12", json=body)


async def test_사장은_멤버의_역할을_바꾼다():
    stub = _StubUseCase()
    response = await _patch(stub, StubShopAccess(OWNER_PERMISSIONS), {"role": "owner"})
    assert response.status_code == 200
    assert response.json() == {"member_id": 12, "user_id": 2, "role": "owner"}
    command = stub.commands[0]
    assert (command.ctx.shop_id, command.member_id, command.role) == (3, 12, "owner")


async def test_권한_없는_직원은_403_이다():
    stub = _StubUseCase()
    response = await _patch(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"), {"role": "owner"})
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_모르는_역할은_422_다():
    response = await _patch(_StubUseCase(), StubShopAccess(OWNER_PERMISSIONS), {"role": "admin"})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_마지막_사장을_낮추면_409_LAST_OWNER_다():
    stub = _StubUseCase(LastOwnerError("매장에는 사장이 한 명 이상 있어야 합니다."))
    response = await _patch(stub, StubShopAccess(OWNER_PERMISSIONS), {"role": "staff"})
    assert (response.status_code, response.json()["code"]) == (409, "LAST_OWNER")


async def test_없는_멤버는_404_MEMBER_NOT_FOUND_다():
    stub = _StubUseCase(MemberNotFoundError("멤버를 찾을 수 없습니다."))
    response = await _patch(stub, StubShopAccess(OWNER_PERMISSIONS), {"role": "staff"})
    assert (response.status_code, response.json()["code"]) == (404, "MEMBER_NOT_FOUND")
