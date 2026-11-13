from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.get_sales_summary_schema import PetCardSchema
from visit.app.dtos.list_due_pets_dto import DuePetsView


class DuePetItemSchema(BaseModel):
    pet: PetCardSchema
    last_visit_date: date       # 마지막으로 다녀간 날(매장 시간대)


class DuePetsSchema(BaseModel):
    """다시 올 때가 지난 아이 — 오래된 순."""

    items: list[DuePetItemSchema]
    next_cursor: str | None

    @classmethod
    def of(cls, view: DuePetsView) -> DuePetsSchema:
        return cls.model_validate(view, from_attributes=True)
