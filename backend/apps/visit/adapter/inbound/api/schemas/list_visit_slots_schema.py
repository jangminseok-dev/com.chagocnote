from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from visit.app.dtos.list_visit_slots_dto import VisitSlotsView


class SlotSchema(BaseModel):
    starts_at: datetime        # 매장 시간대
    warnings: list[str]        # overlap · closed_day · outside_hours


class VisitSlotsSchema(BaseModel):
    date: date
    duration_minutes: int
    closed_day: bool
    slots: list[SlotSchema]

    @classmethod
    def of(cls, view: VisitSlotsView) -> VisitSlotsSchema:
        return cls.model_validate(view, from_attributes=True)
