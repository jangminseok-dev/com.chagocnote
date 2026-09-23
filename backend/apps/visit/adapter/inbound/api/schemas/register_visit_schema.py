from __future__ import annotations

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
)

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.register_visit_dto import RegisteredVisitsView

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

    _pets_unique = field_validator("pet_ids", "menu_ids")(unique_ids)


class RegisteredVisitsSchema(BaseModel):
    visits: list[VisitSchema]
    warnings: list[str]   # overlap · closed_day · outside_hours

    @classmethod
    def of(cls, view: RegisteredVisitsView) -> RegisteredVisitsSchema:
        return cls(visits=[VisitSchema.of(v) for v in view.visits], warnings=view.warnings)
