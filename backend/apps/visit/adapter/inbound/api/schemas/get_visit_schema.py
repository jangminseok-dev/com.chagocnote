from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.get_visit_dto import VisitDetailView


class PreviousVisitSchema(BaseModel):
    visit_id: int
    starts_at: datetime


class VisitDetailSchema(BaseModel):
    visit: VisitSchema
    group: list[VisitSchema]
    previous_visit: PreviousVisitSchema | None
    no_show_count: int

    @classmethod
    def of(cls, view: VisitDetailView) -> VisitDetailSchema:
        return cls.model_validate(view, from_attributes=True)
