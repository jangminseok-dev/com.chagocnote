from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.v1.logout_router import logout_router
from auth.dependencies.logout_provider import get_logout_use_case


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def logout(self, command):
        self.commands.append(command)


async def test_로그아웃은_본문_없이_204를_돌려준다():
    stub = _StubUseCase()
    app = FastAPI()
    app.include_router(logout_router)
    app.dependency_overrides[get_logout_use_case] = lambda: stub
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.post("/v1/auth/logout", json={"refresh_token": "my-refresh"})
    assert response.status_code == 204
    assert response.content == b""
    assert stub.commands[0].refresh_token == "my-refresh"
