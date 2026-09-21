from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tenancy.domain.value_objects.role_code import RoleCode


@dataclass(frozen=True)
class Member:
    """매장에 지금 속해 있는 멤버. 내보낸 멤버는 이 타입으로 나오지 않는다."""

    id: int
    shop_id: int
    user_id: int
    role: RoleCode
    joined_at: datetime
