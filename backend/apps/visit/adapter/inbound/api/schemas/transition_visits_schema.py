from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, unique_ids
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView


class TransitionVisitsRequestSchema(BaseModel):
    """cancel_reason 은 cancel 일 때만, 반드시(어기면 422)."""

    visit_ids: Annotated[list[EntityId], Field(min_length=1, max_length=10)]
    action: Literal["start", "complete", "cancel", "no_show", "revert"]
    cancel_reason: Literal["customer_request", "shop_reason"] | None = None

    _ids_unique = field_validator("visit_ids")(unique_ids)


class TransitionedVisitsSchema(BaseModel):
    visits: list[VisitSchema]

    @classmethod
    def of(cls, view: TransitionedVisitsView) -> TransitionedVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
