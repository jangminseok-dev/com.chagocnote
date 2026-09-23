from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.app.dtos.get_visit_calendar_dto import VisitCalendarView


class CalendarDaySchema(BaseModel):
    date: date
    visit_count: int
    completed_count: int
    open_count: int
    unresolved_count: int
    closed_day: bool


class VisitCalendarSchema(BaseModel):
    month: str                 # 2026-09
    days: list[CalendarDaySchema]
    unresolved_total: int
    oldest_unresolved_date: date | None

    @classmethod
    def of(cls, view: VisitCalendarView) -> VisitCalendarSchema:
        return cls(
            month=f"{view.year:04d}-{view.month:02d}",
            days=[CalendarDaySchema.model_validate(d, from_attributes=True) for d in view.days],
            unresolved_total=view.unresolved_total, oldest_unresolved_date=view.oldest_unresolved_date,
        )
