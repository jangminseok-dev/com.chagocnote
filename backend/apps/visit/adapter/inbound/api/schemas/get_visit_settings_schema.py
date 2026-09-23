from __future__ import annotations

from datetime import time

from pydantic import BaseModel

from visit.app.dtos.schedule_view_dto import VisitSettingsView


class VisitSettingsSchema(BaseModel):
    opens_at: time
    closes_at: time
    default_duration_minutes: int
    closed_weekdays: list[int]   # 월=0 … 일=6

    @classmethod
    def of(cls, view: VisitSettingsView) -> VisitSettingsSchema:
        return cls(opens_at=view.opens_at, closes_at=view.closes_at,
                   default_duration_minutes=view.default_duration_minutes,
                   closed_weekdays=view.closed_weekdays)
