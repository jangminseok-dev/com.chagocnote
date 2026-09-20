"""오류 응답 본문을 {"code", "message"} 한 가지 형식으로 통일한다 — 404·405 포함."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.http_errors import install_error_handlers


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app, {})

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    return app


async def test_없는_경로는_NOT_FOUND_본문을_돌려준다():
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as client:
        response = await client.get("/nope")
    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Not Found"}


async def test_허용되지_않은_메서드는_METHOD_NOT_ALLOWED_본문을_돌려준다():
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as client:
        response = await client.post("/ping")
    assert response.status_code == 405
    assert response.json() == {"code": "METHOD_NOT_ALLOWED", "message": "Method Not Allowed"}
