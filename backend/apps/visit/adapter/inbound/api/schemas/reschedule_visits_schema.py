from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from visit.adapter.inbound.api.schemas.build_send_bundle_schema import BundlePartSchema
from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, unique_ids
from visit.adapter.inbound.api.schemas.series_scope_schema import SeriesScopeFields
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView


class RescheduleVisitsRequestSchema(SeriesScopeFields):
    visit_ids: Annotated[list[EntityId], Field(min_length=1, max_length=10)]
    starts_at: AwareDatetime

    _ids_unique = field_validator("visit_ids")(unique_ids)


class RescheduledVisitsSchema(BaseModel):
    visits: list[VisitSchema]
    warnings: list[str]
    notice: list[BundlePartSchema]   # ⑭ 이후 전부 뒤 보호자에게 보낼 글 — 이 예약만이면 빈 목록

    @classmethod
    def of(cls, view: RescheduledVisitsView) -> RescheduledVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
