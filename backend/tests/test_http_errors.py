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


class _Detailed(Exception):
    code = "SOMETHING_CONFLICT"

    def __init__(self, message: str, details: dict | None) -> None:
        super().__init__(message)
        self.details = details


def _detailed_app(details: dict | None) -> FastAPI:
    app = FastAPI()
    install_error_handlers(app, {_Detailed: 409})

    @app.get("/boom")
    async def boom() -> dict:
        raise _Detailed("걸린 것이 있어요.", details)

    return app


async def test_도메인_오류에_details_가_있으면_본문에_싣는다():
    async with AsyncClient(transport=ASGITransport(app=_detailed_app({"conflicts": [{"visit_id": 3}]})),
                           base_url="http://t") as client:
        response = await client.get("/boom")
    assert response.status_code == 409
    assert response.json() == {"code": "SOMETHING_CONFLICT", "message": "걸린 것이 있어요.",
                               "details": {"conflicts": [{"visit_id": 3}]}}


async def test_details_가_없으면_본문은_두_칸이다():
    async with AsyncClient(transport=ASGITransport(app=_detailed_app(None)), base_url="http://t") as client:
        response = await client.get("/boom")
    assert response.json() == {"code": "SOMETHING_CONFLICT", "message": "걸린 것이 있어요."}
