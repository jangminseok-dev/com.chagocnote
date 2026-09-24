from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RecordItemView:
    menu_id: int
    name: str
    amount: int


@dataclass(frozen=True)
class RecordMediaView:
    """붙은 사진·영상 하나와 그 읽기 URL. 영상은 display_url 이 없고 thumb_url 이 포스터다."""

    media_id: int
    kind: str
    phase: str
    sort_order: int
    original_url: str
    display_url: str | None
    thumb_url: str
    width: int
    height: int
    duration_seconds: int | None


@dataclass(frozen=True)
class RecordView:
    """방문 상세의 '오늘의 케어'와 기록 화면이 쓰는 기록 전체. version 은 다음 PUT 에 그대로 돌려보낸다."""

    visit_id: int
    weight_kg: Decimal | None
    care_note: str | None
    internal_note: str | None
    payment_method: str | None
    total_amount: int | None
    items: list[RecordItemView]
    media: list[RecordMediaView]   # 전 → 후, 각각 순서대로
    version: int
