"""guardian 라우터 테스트가 함께 쓰는 도우미 — 유스케이스를 스텁으로 바꾸고 로그인한 계정을 정해 둔 앱을 만든다."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from guardian.adapter.inbound.api.error_map import GUARDIAN_ERROR_STATUS

USER_ID = 5


class Recorder:
    """유스케이스 스텁 — 받은 명령을 적고 정해 둔 값을 돌려주거나 정해 둔 오류를 던진다."""

    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list = []

    def __getattr__(self, name):
        async def call(command):
            self.calls.append(command)
            if self.error is not None:
                raise self.error
            return self.result

        return call


def build_app(router, slot, stub, *, logged_in: bool = True, overrides: dict | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, GUARDIAN_ERROR_STATUS)
    app.dependency_overrides[slot] = lambda: stub
    app.dependency_overrides[get_db] = lambda: None
    if logged_in:
        app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    for key, value in (overrides or {}).items():
        app.dependency_overrides[key] = value
    return app


def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
