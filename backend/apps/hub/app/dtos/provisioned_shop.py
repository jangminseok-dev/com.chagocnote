from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProvisionedShop:
    """새로 개설한 매장과 사장용 초대 코드. 코드 원문은 여기서만 볼 수 있다 (DB 에는 해시만 남는다)."""

    shop_id: int
    name: str
    owner_invite_code: str
    invite_expires_at: datetime
