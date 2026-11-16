"""매장이 문진표에 더한 질문의 요청·응답(⑪-C)."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictBool, field_validator

from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.domain.entities.intake import IntakeQuestion, QuestionDraft

_MAX_BIGINT = 9_223_372_036_854_775_807


class IntakeQuestionSchema(BaseModel):
    question_id: int
    label: str
    required: bool


class IntakeQuestionsSchema(BaseModel):
    items: list[IntakeQuestionSchema]

    @classmethod
    def of(cls, questions: list[IntakeQuestion]) -> "IntakeQuestionsSchema":
        return cls(items=[
            IntakeQuestionSchema(question_id=q.id, label=q.label, required=q.required) for q in questions])


class IntakeQuestionDraftSchema(BaseModel):
    question_id: Annotated[int, Field(ge=1, le=_MAX_BIGINT)] | None = None
    label: str = Field(max_length=400)      # 길이와 빈 글은 도메인이 본다
    required: StrictBool

    @field_validator("label")
    @classmethod
    def _no_control_chars(cls, value: str) -> str:
        return reject_control_chars(value)


class UpdateIntakeQuestionsRequestSchema(BaseModel):
    """목록 전체. 빠진 질문은 지운 것이다."""

    items: list[IntakeQuestionDraftSchema] = Field(max_length=20)

    def to_drafts(self) -> tuple[QuestionDraft, ...]:
        return tuple(QuestionDraft(id=i.question_id, label=i.label, required=i.required) for i in self.items)
