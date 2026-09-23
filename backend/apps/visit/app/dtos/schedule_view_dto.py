from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings


@dataclass(frozen=True)
class VisitSettingsView:
    opens_at: time
    closes_at: time
    default_duration_minutes: int
    closed_weekdays: list[int]   # 월=0 … 일=6, 오름차순

    @classmethod
    def of(cls, settings: ScheduleSettings) -> VisitSettingsView:
        return cls(opens_at=settings.opens_at, closes_at=settings.closes_at,
                   default_duration_minutes=settings.default_duration_minutes,
                   closed_weekdays=sorted(settings.closed_weekdays))


@dataclass(frozen=True)
class ClosedDateView:
    date: date
    note: str | None

    @classmethod
    def of(cls, closed: ClosedDate) -> ClosedDateView:
        return cls(date=closed.day, note=closed.note)
