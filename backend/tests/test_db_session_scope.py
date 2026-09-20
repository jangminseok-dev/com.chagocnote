"""get_db 커밋이 응답을 보내기 전에 끝나는지 확인한다."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import core.database
from core.database import DbSession
from core.http_errors import ApiError, install_error_handlers


class _StubSession:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def __aenter__(self) -> "_StubSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def commit(self) -> None:
        self._events.append("commit")

    async def rollback(self) -> None:
        self._events.append("rollback")


def _wrap(app, events: list[str]):
    async def wrapped(scope, receive, send):
        async def send_wrapper(message):
            if message["type"] == "http.response.body":
                events.append("response-body-sent")
            await send(message)

        await app(scope, receive, send_wrapper)

    return wrapped


@pytest.fixture
def events(monkeypatch):
    recorded: list[str] = []
    monkeypatch.setattr(core.database, "_session_factory", lambda: _StubSession(recorded))
    return recorded


async def test_커밋은_응답을_보내기_전에_끝난다(events):
    app = FastAPI()

    @app.get("/ping")
    async def ping(db: DbSession) -> dict:
        events.append("handler-return")
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=_wrap(app, events)), base_url="http://t"
    ) as client:
        response = await client.get("/ping")

    assert response.status_code == 200
    assert events == ["handler-return", "commit", "response-body-sent"]


async def test_핸들러가_실패하면_롤백하고_커밋하지_않는다(events):
    app = FastAPI()
    install_error_handlers(app, {})

    @app.get("/boom")
    async def boom(db: DbSession) -> dict:
        raise ApiError(400, "X", "x")

    async with AsyncClient(
        transport=ASGITransport(app=_wrap(app, events)), base_url="http://t"
    ) as client:
        response = await client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {"code": "X", "message": "x"}
    assert "rollback" in events
    assert "commit" not in events
