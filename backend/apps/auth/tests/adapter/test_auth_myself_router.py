from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.v1.auth_myself_router import auth_myself_router


async def test_myself_는_인증_없이_200과_자기소개를_돌려준다():
    app = FastAPI()
    app.include_router(auth_myself_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/auth/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "인증 (auth)"
    assert "/v1/auth/social" in body["introduction"]
