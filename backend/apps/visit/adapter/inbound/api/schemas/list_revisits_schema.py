from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.get_sales_summary_schema import PetCardSchema
from visit.app.dtos.count_revisits_dto import RevisitCountsView
from visit.app.dtos.list_revisits_dto import RevisitsView


class RevisitItemSchema(BaseModel):
    """다시 올 때가 된 아이 한 줄(⑬ 설계 3.3) — 돈이 없다(직원도 본다). 안내 글에 보호자 이름·번호가 없다."""

    pet: PetCardSchema
    last_visit_date: date
    last_visit_id: int
    cycle_weeks: int
    cycle_source: str            # manual · computed · single · none
    last_interval_weeks: int | None
    due_date: date
    estimated: bool
    nudged_on: date | None
    message: str


class RevisitsSchema(BaseModel):
    items: list[RevisitItemSchema]
    next_cursor: str | None

    @classmethod
    def of(cls, view: RevisitsView) -> RevisitsSchema:
        return cls.model_validate(view, from_attributes=True)


class RevisitCountsSchema(BaseModel):
    soon: int
    due: int

    @classmethod
    def of(cls, view: RevisitCountsView) -> RevisitCountsSchema:
        return cls(soon=view.soon, due=view.due)
