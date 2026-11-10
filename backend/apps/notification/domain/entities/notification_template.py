from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from notification.domain.value_objects.template_status import PENDING


@dataclass(frozen=True)
class NotificationTemplate:
    """매장 채널에 등록한 종류별 템플릿 한 줄(설계 4.3). 문안은 코드에 있고(text_version) 여기엔 심사 상태만 있다.

    승인된 종류를 새 판으로 재등록하면 새 판은 대기 칸(pending_*)에 들고 본 칸은 그대로다 — 심사가 끝날 때까지 옛 판으로
    계속 보낸다(설계 2026-11-10 3.2). 승인되면 대기 판이 본 칸으로 올라가고, 반려되면 대기 칸만 비운다.
    """

    id: int
    shop_id: int
    kind: str
    text_version: int
    provider_template_id: str
    status: str
    rejected_reason: str | None
    requested_at: datetime
    decided_at: datetime | None
    pending_text_version: int | None = None
    pending_provider_template_id: str | None = None

    @property
    def under_review(self) -> bool:
        """업체에 심사 결과를 물어야 한다 — 첫 판이 심사 중이거나 승인된 줄에 새 판이 걸려 있다."""
        return self.status == PENDING or self.pending_provider_template_id is not None

    @property
    def review_provider_template_id(self) -> str:
        """심사 결과를 물을 업체 템플릿 ID — 대기 판이 있으면 그것, 없으면 본 칸."""
        return self.pending_provider_template_id or self.provider_template_id
