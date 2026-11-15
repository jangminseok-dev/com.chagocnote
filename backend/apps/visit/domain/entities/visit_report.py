from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VisitReport:
    """알림장 링크 하나(설계 4.1). 방문의 기록을 비추는 창이고 내용을 갖지 않는다.

    토큰은 저장하지 않는다 — public_id 와 서버 키로 그때마다 계산한다(core/link_token.py).
    """

    id: int
    visit_id: int
    public_id: bytes
    expires_at: datetime | None       # None 이면 무기한
    revoked_at: datetime | None       # 끊은 시각
    first_viewed_at: datetime | None  # 보호자가 처음 연 시각
    created_by_member_id: int
    created_at: datetime              # 보낸 시각

    def is_live(self, now: datetime) -> bool:
        """끊지 않았고 기간이 지나지 않았다. 기간이 끝나는 바로 그 시각에는 닫힌 것이다."""
        return self.revoked_at is None and (self.expires_at is None or self.expires_at > now)
