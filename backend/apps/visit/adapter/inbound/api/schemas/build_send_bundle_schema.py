from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.build_send_bundle_dto import BundlePartView


class BundlePartSchema(BaseModel):
    kind: str
    text: str


class SendBundleSchema(BaseModel):
    """보호자에게 보낼 글의 토막들. 앱은 모르는 kind 도 글 그대로 싣는다."""

    parts: list[BundlePartSchema]

    @classmethod
    def of(cls, parts: list[BundlePartView]) -> "SendBundleSchema":
        return cls(parts=[BundlePartSchema(kind=part.kind, text=part.text) for part in parts])
