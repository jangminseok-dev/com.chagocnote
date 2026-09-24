from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from visit.domain.entities.visit_record import RecordItem


@dataclass(frozen=True)
class MediaPlacement:
    """요청이 정한 미디어의 자리. 종류는 아직 모른다 — 가져가기(claim) 뒤에 안다."""

    media_id: int
    phase: str
    sort_order: int


@dataclass(frozen=True)
class RecordInput:
    """기록 전체 교체(PUT)의 내용. 비운 칸은 지운다."""

    weight_kg: Decimal | None
    care_note: str | None
    internal_note: str | None
    payment_method: str | None
    total_amount: int | None
    items: tuple[RecordItem, ...]
    media: tuple[MediaPlacement, ...]

    @property
    def has_money(self) -> bool:
        """돈 칸 — 총액·항목·결제 수단. 하나라도 있으면 sales:write 가 필요하다(설계 8절)."""
        return self.total_amount is not None or bool(self.items) or self.payment_method is not None
