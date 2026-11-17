from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.register_visit_dto import RegisteredVisitsView
from visit.domain.services.visit_series import MAX_COUNT, MAX_INTERVAL_WEEKS, MIN_COUNT, MIN_INTERVAL_WEEKS

_MAX_BIGINT = 9_223_372_036_854_775_807

EntityId = Annotated[StrictInt, Field(ge=1, le=_MAX_BIGINT)]
Memo = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500),
    AfterValidator(lambda v: reject_control_chars(v, allow_newline=True)),
] | None


def unique_ids(ids: list[int]) -> list[int]:
    if len(set(ids)) != len(ids):
        raise ValueError("같은 ID 를 두 번 보낼 수 없습니다.")
    return ids


class RepeatSchema(BaseModel):
    """반복 예약(⑭) — interval_weeks 주마다 count 번(첫 예약 포함). skip 은 빼는 회차 번호(1~count, 중복 없음)."""

    interval_weeks: Annotated[StrictInt, Field(ge=MIN_INTERVAL_WEEKS, le=MAX_INTERVAL_WEEKS)]
    count: Annotated[StrictInt, Field(ge=MIN_COUNT, le=MAX_COUNT)]
    skip: Annotated[list[Annotated[StrictInt, Field(ge=1, le=MAX_COUNT)]], Field(max_length=MAX_COUNT - 1)] = []

    _skip_unique = field_validator("skip")(unique_ids)

    @model_validator(mode="after")
    def _skip_within_count(self) -> RepeatSchema:
        if any(n > self.count for n in self.skip):
            raise ValueError("없는 회차는 뺄 수 없습니다.")
        return self


class RegisterVisitRequestSchema(BaseModel):
    """예약 등록. starts_at 은 시간대가 붙은 시각이어야 한다(예: 2026-10-02T14:00:00+09:00).
    walk_in 이면 starts_at 을 보내지 않는다 — 지금 시작한 손님이다."""

    customer_id: EntityId
    pet_ids: Annotated[list[EntityId], Field(max_length=10)] = []
    starts_at: AwareDatetime | None = None
    duration_minutes: StrictInt | None = None
    menu_ids: Annotated[list[EntityId], Field(max_length=10)] = []
    memo: Memo = None
    walk_in: StrictBool = False
    repeat: RepeatSchema | None = None   # ⑭ 반복 예약 — 없으면 한 번

    _pets_unique = field_validator("pet_ids", "menu_ids")(unique_ids)


class SeriesOccurrenceSchema(BaseModel):
    starts_at: datetime
    warnings: list[str]


class RegisteredSeriesSchema(BaseModel):
    id: int
    interval_weeks: int
    occurrences: list[SeriesOccurrenceSchema]


class RegisteredVisitsSchema(BaseModel):
    visits: list[VisitSchema]
    warnings: list[str]   # overlap · closed_day · outside_hours (반복이면 첫 회차의 것)
    series: RegisteredSeriesSchema | None = None

    @classmethod
    def of(cls, view: RegisteredVisitsView) -> RegisteredVisitsSchema:
        series = None
        if view.series is not None:
            series = RegisteredSeriesSchema.model_validate(view.series, from_attributes=True)
        return cls(visits=[VisitSchema.of(v) for v in view.visits], warnings=view.warnings, series=series)
