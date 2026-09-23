from __future__ import annotations

from datetime import time
from typing import Annotated

from pydantic import BaseModel, Field, StrictInt

from visit.domain.value_objects.schedule_settings import ScheduleSettings

Weekday = Annotated[StrictInt, Field(ge=0, le=6)]


class UpdateVisitSettingsRequestSchema(BaseModel):
    """영업시간(10분 단위), 기본 소요(10분 단위 10~600), 쉬는 요일(월=0 … 일=6)."""

    opens_at: time
    closes_at: time
    default_duration_minutes: StrictInt
    closed_weekdays: Annotated[list[Weekday], Field(max_length=7)]

    def to_settings(self) -> ScheduleSettings:
        return ScheduleSettings(
            opens_at=self.opens_at, closes_at=self.closes_at,
            default_duration_minutes=self.default_duration_minutes,
            closed_weekdays=frozenset(self.closed_weekdays),
        )
