from __future__ import annotations

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import MenuBriefSchema
from visit.app.dtos.get_visit_defaults_dto import VisitDefaultsView


class VisitDefaultsSchema(BaseModel):
    source_visit_id: int | None
    duration_minutes: int
    menus: list[MenuBriefSchema]

    @classmethod
    def of(cls, view: VisitDefaultsView) -> VisitDefaultsSchema:
        return cls.model_validate(view, from_attributes=True)
