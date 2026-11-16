from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.get_day_wrap_up_dto import DayWrapUpView


class WrapUpPrefillSchema(BaseModel):
    """결제 장에 채워 둘 값 — 금액을 적는 장이라 sales:write 가 있을 때만 그 장이 나온다(⑬ R3)."""

    total_amount: int | None
    payment_method: Literal["card", "cash", "transfer"] | None


class WrapUpCardSchema(BaseModel):
    kind: Literal["unresolved", "unpaid", "report_unsent"]
    visit: VisitSchema
    photo_url: str | None   # 아이의 프로필 사진 썸네일
    prefill: WrapUpPrefillSchema | None   # 결제 장(unpaid)에만


class DayWrapUpSchema(BaseModel):
    date: date
    cards: list[WrapUpCardSchema]   # 정리 안 된 예약 → 결제 안 적음 → 알림장 안 보냄, 그 안에서 시작 순

    @classmethod
    def of(cls, view: DayWrapUpView) -> DayWrapUpSchema:
        return cls.model_validate(view, from_attributes=True)
