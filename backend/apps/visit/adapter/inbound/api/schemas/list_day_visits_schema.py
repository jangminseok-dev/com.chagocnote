from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.list_day_visits_dto import DayVisitsView


class DayCountsSchema(BaseModel):
    visit_count: int   # 마릿수 — 예약됨·미용 중·완료
    reserved: int
    in_progress: int
    completed: int
    canceled: int
    no_show: int
    unresolved: int


class DayVisitItemSchema(BaseModel):
    visit: VisitSchema
    group_key: str
    overlapping: bool
    unresolved: bool
    has_record: bool
    cover: str | None   # 대표 사진 썸네일 URL


class DayVisitsSchema(BaseModel):
    date: date
    closed_day: bool
    counts: DayCountsSchema
    items: list[DayVisitItemSchema]

    @classmethod
    def of(cls, view: DayVisitsView) -> DayVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
