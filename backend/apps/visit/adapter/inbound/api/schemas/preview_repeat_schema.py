from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.app.dtos.preview_repeat_dto import RepeatPreviewView


class OccurrenceSchema(BaseModel):
    index: int
    starts_at: datetime
    warnings: list[str]      # overlap · closed_day · outside_hours
    taken: bool


class RepeatPreviewSchema(BaseModel):
    interval_weeks: int
    count: int
    occurrences: list[OccurrenceSchema]
    beyond_horizon: int

    @classmethod
    def of(cls, view: RepeatPreviewView) -> RepeatPreviewSchema:
        return cls.model_validate(view, from_attributes=True)
