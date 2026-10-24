from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewMessage:
    """새로 넣을 알림 줄 하나 — 저장소 create 의 입력. 즉시 보낼 것은 scheduled_at 이 만든 시각이다."""

    shop_id: int
    visit_id: int
    customer_id: int
    pet_id: int | None
    kind: str
    scheduled_at: datetime            # UTC
    variables: Mapping[str, str]      # 이벤트에서만 알 수 있는 값(알림장 주소·기간, 바뀌기 전 시각 …)
    requested_by_member_id: int | None = None   # 매장이 [다시 보내기]로 만든 줄이면 멤버 ID
