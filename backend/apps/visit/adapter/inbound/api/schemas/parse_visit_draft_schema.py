from __future__ import annotations

from datetime import date, time
from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints, field_serializer

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.app.dtos.parse_visit_draft_dto import VisitDraftView

MAX_DRAFT_TEXT = 1000


class VisitDraftRequestSchema(BaseModel):
    """카톡에서 붙여넣거나 공유받은 글. 1,000자까지, 줄바꿈 말고는 제어 문자를 받지 않는다."""

    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_DRAFT_TEXT),
        AfterValidator(lambda v: reject_control_chars(v, allow_newline=True)),
    ]


class DraftPetSchema(BaseModel):
    pet_id: int
    name: str


class DraftCandidateSchema(BaseModel):
    customer_id: int
    name: str
    phone_masked: str
    pets: list[DraftPetSchema]
    matched_pet_ids: list[int]


class DraftGuessSchema(BaseModel):
    date: bool
    time: bool
    who: bool
    menu: bool


class VisitDraftSchema(BaseModel):
    date: date | None
    time: time | None   # HH:MM 으로 나간다(계약) — 앱이 시간 칸의 at 로 그대로 쓴다
    customer_candidates: list[DraftCandidateSchema]
    pet_ids: list[int]
    menu_ids: list[int]
    guessed: DraftGuessSchema

    @field_serializer("time")
    def _hhmm(self, value: time | None) -> str | None:
        return None if value is None else value.strftime("%H:%M")

    @classmethod
    def of(cls, view: VisitDraftView) -> VisitDraftSchema:
        return cls.model_validate(view, from_attributes=True)
