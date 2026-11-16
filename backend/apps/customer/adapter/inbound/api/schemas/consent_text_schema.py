"""매장이 고치는 동의서 글의 요청·응답(⑪-B)."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.app.dtos.consent_text_view_dto import ConsentTextView


class ConsentTextSchema(BaseModel):
    part: str
    body: str
    edited: bool
    default_body: str

    @classmethod
    def of(cls, view: ConsentTextView) -> "ConsentTextSchema":
        return cls(part=view.part, body=view.body, edited=view.edited, default_body=view.default_body)


class ConsentTextsSchema(BaseModel):
    parts: list[ConsentTextSchema]

    @classmethod
    def of(cls, views: list[ConsentTextView]) -> "ConsentTextsSchema":
        return cls(parts=[ConsentTextSchema.of(view) for view in views])


class UpdateConsentTextRequestSchema(BaseModel):
    """body 가 null 이면 기본 글로 되돌린다. 길이와 빈 글은 도메인이 본다."""

    body: str | None = Field(max_length=8000)

    @field_validator("body")
    @classmethod
    def _no_control_chars(cls, value: str | None) -> str | None:
        return reject_control_chars(value, allow_newline=True)
