from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.app.dtos.schedule_view_dto import ClosedDateView


class ClosedDateSchema(BaseModel):
    date: date
    note: str | None

    @classmethod
    def of(cls, view: ClosedDateView) -> ClosedDateSchema:
        return cls(date=view.date, note=view.note)


class ClosedDateListSchema(BaseModel):
    items: list[ClosedDateSchema]
