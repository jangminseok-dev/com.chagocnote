from __future__ import annotations

from datetime import time
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StrictInt

from visit.domain.value_objects.schedule_settings import ScheduleSettings

Weekday = Annotated[StrictInt, Field(ge=0, le=6)]


def _reject_tzinfo(value: time) -> time:
    """시간대가 붙은 값은 거절한다 — aware/naive 비교가 섞이면 check_settings 가 TypeError 로 500 이 된다."""
    if value.tzinfo is not None:
        raise ValueError("영업시간에는 시간대를 붙일 수 없습니다.")
    return value


LocalTime = Annotated[time, AfterValidator(_reject_tzinfo)]


class UpdateVisitSettingsRequestSchema(BaseModel):
    """영업시간(10분 단위), 기본 소요(10분 단위 10~600), 쉬는 요일(월=0 … 일=6)."""

    opens_at: LocalTime
    closes_at: LocalTime
    default_duration_minutes: StrictInt
    closed_weekdays: Annotated[list[Weekday], Field(max_length=7)]

    def to_settings(self) -> ScheduleSettings:
        return ScheduleSettings(
            opens_at=self.opens_at, closes_at=self.closes_at,
            default_duration_minutes=self.default_duration_minutes,
            closed_weekdays=frozenset(self.closed_weekdays),
        )
