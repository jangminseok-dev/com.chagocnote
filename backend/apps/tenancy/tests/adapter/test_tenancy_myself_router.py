from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router


async def test_myself_는_인증_없이_200과_자기소개를_돌려준다():
    app = FastAPI()
    app.include_router(tenancy_myself_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/shops/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "매장 (tenancy)"
    assert "/v1/invites/accept" in body["introduction"]
