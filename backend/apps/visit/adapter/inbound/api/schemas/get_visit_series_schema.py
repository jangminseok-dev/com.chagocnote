from __future__ import annotations

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.get_visit_series_dto import VisitSeriesView


class VisitSeriesSchema(BaseModel):
    id: int
    interval_weeks: int
    visits: list[VisitSchema]

    @classmethod
    def of(cls, view: VisitSeriesView) -> VisitSeriesSchema:
        return cls(id=view.id, interval_weeks=view.interval_weeks, visits=[VisitSchema.of(v) for v in view.visits])
