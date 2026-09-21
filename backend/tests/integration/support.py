"""실제 배선 통합 테스트가 함께 쓰는 도우미."""
from __future__ import annotations

from dataclasses import dataclass

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class Wired:
    auth: AsyncClient   # 인증 프로세스 (auth_main.app)
    api: AsyncClient    # API 프로세스 (main.app)
    engine: AsyncEngine

    async def login(self, name: str) -> dict:
        response = await self.auth.post("/v1/auth/social", json={"provider": "dev", "token": name})
        assert response.status_code == 200, response.text
        return response.json()

    async def execute(self, sql: str, **params) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(text(sql), params)
