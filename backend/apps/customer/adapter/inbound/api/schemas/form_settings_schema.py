"""서류 설정의 요청·응답(⑪-B)."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictBool, field_validator

from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.domain.services.form_settings_rules import DEFAULT_CONSENT_TEXT, DEFAULT_RESERVATION_TEXT
from customer.domain.value_objects.form_settings import DEFAULT_FORM_SETTINGS, FormSettings


class FormSettingsValuesSchema(BaseModel):
    link_days: int
    senior_age: int
    consent_days: int
    reservation_text: str
    consent_text: str
    intake_keep_days: int
    intake_hidden: list[str]
    intake_consent_all: bool

    @classmethod
    def of(cls, settings: FormSettings) -> "FormSettingsValuesSchema":
        return cls(
            link_days=settings.link_days, senior_age=settings.senior_age, consent_days=settings.consent_days,
            # 고치지 않은 글은 기본 글을 싣는다 — 화면에 빈칸이 없다.
            reservation_text=settings.reservation_text or DEFAULT_RESERVATION_TEXT,
            consent_text=settings.consent_text or DEFAULT_CONSENT_TEXT,
            intake_keep_days=settings.intake_keep_days, intake_hidden=list(settings.intake_hidden),
            intake_consent_all=settings.intake_consent_all,
        )


class FormSettingsSchema(FormSettingsValuesSchema):
    defaults: FormSettingsValuesSchema   # 화면의 [기본값으로]가 쓴다

    @classmethod
    def of(cls, settings: FormSettings) -> "FormSettingsSchema":
        values = FormSettingsValuesSchema.of(settings)
        return cls(**values.model_dump(), defaults=FormSettingsValuesSchema.of(DEFAULT_FORM_SETTINGS))


class UpdateFormSettingsRequestSchema(BaseModel):
    """전체 교체. 글이 null 이면 기본 글로 되돌린다. 범위와 글의 규칙은 도메인이 본다."""

    link_days: int = Field(ge=-32768, le=32767)
    senior_age: int = Field(ge=-32768, le=32767)
    consent_days: int = Field(ge=-32768, le=32767)
    reservation_text: str | None = Field(default=None, max_length=2000)
    consent_text: str | None = Field(default=None, max_length=2000)
    # 문진표의 두 칸(⑪-C)은 선택이다 — 빠지면 지금 값을 둔다. 이 칸을 모르는 예전 앱이 다섯 칸만 보내도 지워지지 않는다.
    intake_keep_days: int | None = Field(default=None, ge=-32768, le=32767)
    intake_hidden: list[Annotated[str, Field(max_length=20)]] | None = Field(default=None, max_length=20)
    intake_consent_all: StrictBool | None = None      # ⑪-C1b — 빠지면 지금 값

    @field_validator("reservation_text", "consent_text")
    @classmethod
    def _no_control_chars(cls, value: str | None) -> str | None:
        return reject_control_chars(value, allow_newline=True)

    def kept(self) -> frozenset[str]:
        """보내지 않은 칸 — 지금 값을 그대로 둔다."""
        return frozenset(
            name for name in ("intake_keep_days", "intake_hidden", "intake_consent_all") if getattr(self, name) is None)

    def to_settings(self) -> FormSettings:
        def text(value: str | None, default: str) -> str | None:
            # 기본 글 그대로 보내면 고치지 않은 것으로 둔다 — 기본 글이 바뀌면 따라간다.
            return None if value is None or value == default else value

        return FormSettings(
            link_days=self.link_days, senior_age=self.senior_age, consent_days=self.consent_days,
            reservation_text=text(self.reservation_text, DEFAULT_RESERVATION_TEXT),
            consent_text=text(self.consent_text, DEFAULT_CONSENT_TEXT),
            intake_keep_days=(
                DEFAULT_FORM_SETTINGS.intake_keep_days if self.intake_keep_days is None else self.intake_keep_days),
            intake_hidden=() if self.intake_hidden is None else tuple(self.intake_hidden),
            intake_consent_all=bool(self.intake_consent_all),
        )
