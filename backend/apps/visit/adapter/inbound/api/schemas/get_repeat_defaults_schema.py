from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.get_repeat_defaults_dto import RepeatDefaultsView


class RepeatDefaultsSchema(BaseModel):
    interval_weeks: int
    source: str               # cycle · shop
    pet_id: int | None
    cycle_weeks: int | None
    count: int

    @classmethod
    def of(cls, view: RepeatDefaultsView) -> RepeatDefaultsSchema:
        return cls.model_validate(view, from_attributes=True)
