from __future__ import annotations

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.check_view_schema import CheckSchema
from visit.app.dtos.get_visit_checks_dto import VisitChecksView


class PetChecksSchema(BaseModel):
    pet_id: int
    checks: list[CheckSchema]


class VisitChecksSchema(BaseModel):
    customer: list[CheckSchema]
    pets: list[PetChecksSchema]

    @classmethod
    def of(cls, view: VisitChecksView) -> VisitChecksSchema:
        return cls.model_validate(view, from_attributes=True)
