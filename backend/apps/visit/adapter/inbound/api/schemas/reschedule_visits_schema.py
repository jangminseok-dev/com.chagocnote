from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, unique_ids
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView


class RescheduleVisitsRequestSchema(BaseModel):
    visit_ids: Annotated[list[EntityId], Field(min_length=1, max_length=10)]
    starts_at: AwareDatetime

    _ids_unique = field_validator("visit_ids")(unique_ids)


class RescheduledVisitsSchema(BaseModel):
    visits: list[VisitSchema]
    warnings: list[str]

    @classmethod
    def of(cls, view: RescheduledVisitsView) -> RescheduledVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
