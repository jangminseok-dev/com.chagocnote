from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import MenuBriefSchema
from visit.app.dtos.get_next_visit_draft_dto import NextVisitDraftView


class NextVisitDraftSchema(BaseModel):
    customer_id: int
    pet_ids: list[int]
    starts_at: datetime
    duration_minutes: int
    menus: list[MenuBriefSchema]
    interval_weeks: int

    @classmethod
    def of(cls, view: NextVisitDraftView) -> NextVisitDraftSchema:
        return cls.model_validate(view, from_attributes=True)
