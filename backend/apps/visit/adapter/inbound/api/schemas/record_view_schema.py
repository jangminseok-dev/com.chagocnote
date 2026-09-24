"""기록 응답 모양 — 기록 쓰기·덧붙이기·방문 상세가 함께 쓴다(app 의 record_view_dto 와 짝)."""
from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.record_view_dto import RecordView


class RecordItemSchema(BaseModel):
    menu_id: int
    name: str
    amount: int


class RecordMediaSchema(BaseModel):
    media_id: int
    kind: str                 # photo · video
    phase: str                # before · after
    sort_order: int
    original_url: str
    display_url: str | None   # 영상이면 None
    thumb_url: str            # 영상이면 포스터
    width: int
    height: int
    duration_seconds: int | None


class RecordSchema(BaseModel):
    visit_id: int
    weight_kg: float | None   # JSON 숫자로 내보낸다(customer 와 같은 관례)
    care_note: str | None
    internal_note: str | None
    payment_method: str | None
    total_amount: int | None
    items: list[RecordItemSchema]
    media: list[RecordMediaSchema]
    version: int              # 다음 PUT 에 그대로 보낸다

    @classmethod
    def of(cls, view: RecordView) -> RecordSchema:
        return cls.model_validate(view, from_attributes=True)
