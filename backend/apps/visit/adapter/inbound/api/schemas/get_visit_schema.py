from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.get_visit_dto import VisitDetailView


class PreviousVisitSchema(BaseModel):
    visit_id: int
    starts_at: datetime
    cover: str | None


class VisitDetailSchema(BaseModel):
    visit: VisitSchema
    group: list[VisitSchema]
    previous_visit: PreviousVisitSchema | None
    no_show_count: int
    record: RecordSchema | None   # 미용 기록 — 없으면 null
    cover: str | None             # 대표 사진 썸네일 URL

    @classmethod
    def of(cls, view: VisitDetailView) -> VisitDetailSchema:
        return cls.model_validate(view, from_attributes=True)
