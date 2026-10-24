"""notification 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다(visit 과 같다)."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
from notification.tests.helpers.builders import OWNER_PERMISSIONS, STAFF_PERMISSIONS, TZ


class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=OWNER_PERMISSIONS, role="owner"):
        self.permissions = frozenset(permissions)
        self.role = role

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role=self.role, permissions=self.permissions,
                           timezone=TZ)


OWNER = StubShopAccess()
STAFF = StubShopAccess(STAFF_PERMISSIONS, role="staff")


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None) -> FastAPI:
    """access=None 이면 사장 권한으로 통과시킨다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, NOTIFICATION_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_current_user_id] = lambda: 5
    app.dependency_overrides[get_shop_access_port] = lambda: access or OWNER
    return app


def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def error_of(response) -> tuple[int, str]:
    return (response.status_code, response.json()["code"])


class Recorder:
    """유스케이스 스텁 — 받은 명령을 남기고, 정해 둔 값을 돌려주거나 오류를 던진다."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def __getattr__(self, name):
        async def call(command):
            self.calls.append(command)
            if self.error:
                raise self.error
            return self.result

        return call
