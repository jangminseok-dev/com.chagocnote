"""tenancy 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다."""
from __future__ import annotations

from fastapi import FastAPI

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS

STAFF_PERMISSIONS = ("reservation:write", "customer:write", "record:write", "sales:write")
OWNER_PERMISSIONS = STAFF_PERMISSIONS + (
    "sales:read", "record:delete", "customer:delete", "member:manage", "shop:update",
)


class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=(), role="owner", member_id=11):
        self.permissions = frozenset(permissions)
        self.role = role
        self.member_id = member_id
        self.calls = []

    async def resolve(self, user_id, shop_id):
        self.calls.append((user_id, shop_id))
        return ShopContext(
            shop_id=shop_id, member_id=self.member_id, role=self.role, permissions=self.permissions
        )


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None, user_id=5) -> FastAPI:
    """user_id=None 이면 토큰 없는 요청이 된다. access=None 이면 매장 접근 확인 자리를 채우지 않는다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, TENANCY_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    if access is not None:
        app.dependency_overrides[get_shop_access_port] = lambda: access
    return app
