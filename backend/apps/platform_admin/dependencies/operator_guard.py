"""운영자 표면의 관문 — 라우터 수준에서 플랫폼 운영자인지 확인한다.

매장 범위가 core/shop_guard.py 의 require_permission 을 쓰듯, 운영자 표면은 이 가드를 쓴다.
라우터에 dependencies=[Depends(require_operator)] 로 걸어야 하고, 유스케이스는 다시 확인하지 않는다.
"""
from __future__ import annotations

from fastapi import Depends

from core.security import get_current_user_id
from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from platform_admin.dependencies.hub_ports import get_operator_directory
from platform_admin.domain.errors import NotAnOperatorError


async def require_operator(
    user_id: int = Depends(get_current_user_id),
    operators: OperatorDirectoryPort = Depends(get_operator_directory),
) -> int:
    if not await operators.is_operator(user_id):
        raise NotAnOperatorError("플랫폼 운영자만 쓸 수 있습니다.")
    return user_id
