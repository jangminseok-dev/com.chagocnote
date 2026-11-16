from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FamilyInvite:
    """기본 보호자가 가족에게 보내는 초대 하나(⑫ 설계 3.5). 코드는 저장하지 않는다 — SHA-256 만 있다.

    24시간 · 한 번만 쓰인다 · 새로 만들면 앞의 안 쓴 것은 죽는다.
    """

    id: int
    link_id: int                  # 기본 연결
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and self.revoked_at is None and self.expires_at > now
