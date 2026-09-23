"""방문 응답 모양 — 여러 슬라이스가 함께 쓴다(app 의 visit_view_dto 와 짝)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.app.dtos.visit_view_dto import VisitView


class MenuBriefSchema(BaseModel):
    menu_id: int
    name: str


class CustomerBriefSchema(BaseModel):
    customer_id: int
    name: str | None          # 익명화한 고객이면 None
    phone_masked: str | None


class PetBriefSchema(BaseModel):
    pet_id: int
    name: str | None
    species: str
    breed: str
    weight_kg: float   # JSON 숫자로 내보낸다(customer 와 같은 관례)


class VisitSchema(BaseModel):
    visit_id: int
    customer: CustomerBriefSchema
    pet: PetBriefSchema | None   # None 이면 보호자만의 방문
    starts_at: datetime          # 매장 시간대
    ends_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    cancel_reason: str | None
    memo: str | None
    menus: list[MenuBriefSchema]
    status_changed_by_member_id: int | None

    @classmethod
    def of(cls, view: VisitView) -> VisitSchema:
        return cls.model_validate(view, from_attributes=True)
