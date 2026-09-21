"""매장 범위 경로의 관문 — 소속과 권한을 매 요청마다 확인하고 ShopContext 를 돌려준다.

확인 자체는 허브의 ShopAccessPort 가 한다 (구현: tenancy). 스포크가 tenancy 를 import 하면
허브-스포크 위반이라, 모든 매장 범위 스포크가 함께 쓰는 이 의존성은 core 에 둔다.
"""
from __future__ import annotations

from fastapi import Depends

from core.http_errors import ApiError
from core.security import get_current_user_id
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.shop_access_port import ShopAccessPort


def get_shop_access_port() -> ShopAccessPort:
    """허브 포트 자리. 진입점이 app.dependency_overrides 로 tenancy 의 구현을 꽂는다."""
    raise RuntimeError("ShopAccessPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


async def get_shop_context(
    shop_id: int,
    user_id: int = Depends(get_current_user_id),
    access: ShopAccessPort = Depends(get_shop_access_port),
) -> ShopContext:
    """소속만 확인한다. shop_id 는 경로 변수에서 온다."""
    return await access.resolve(user_id, shop_id)


def require_permission(permission: str):
    """소속에 더해 권한까지 확인하는 의존성을 만든다. 예: Depends(require_permission("member:manage"))"""

    async def _guard(ctx: ShopContext = Depends(get_shop_context)) -> ShopContext:
        if permission not in ctx.permissions:
            raise ApiError(403, "PERMISSION_DENIED", "이 작업을 할 권한이 없습니다.")
        return ctx

    return _guard
