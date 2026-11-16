from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.build_send_bundle_dto import SendBundleView


class BundlePartSchema(BaseModel):
    kind: str
    text: str


class SendBundleSchema(BaseModel):
    """보호자에게 보낼 글의 토막들. 앱은 모르는 kind 도 글 그대로 싣는다."""

    parts: list[BundlePartSchema]
    created_form_id: int | None      # 이 조립이 새로 만든 동의서 링크 — 보내지 않으면 앱이 끊는다

    @classmethod
    def of(cls, view: SendBundleView) -> "SendBundleSchema":
        return cls(
            parts=[BundlePartSchema(kind=part.kind, text=part.text) for part in view.parts],
            created_form_id=view.created_form_id,
        )
