from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt

from media.app.dtos.issue_upload_dto import IssuedUploadView

Side = Annotated[StrictInt, Field(ge=1, le=32_767)]


class IssueUploadRequestSchema(BaseModel):
    """형식·크기·길이의 규칙은 도메인(`media_rules`)이 본다. 여기서는 DB 칸에 들어갈 수 있는 범위만."""

    kind: Literal["photo", "video"]
    content_type: Annotated[str, Field(min_length=1, max_length=50)]
    byte_size: Annotated[StrictInt, Field(ge=1, le=2**40)]
    width: Side
    height: Side
    duration_seconds: Annotated[StrictInt, Field(ge=0, le=32_767)] | None = None


class UploadTargetsSchema(BaseModel):
    original: str
    display: str | None   # 영상이면 None
    thumb: str


class IssuedUploadSchema(BaseModel):
    media_id: int
    puts: UploadTargetsSchema
    expires_at: datetime

    @classmethod
    def of(cls, view: IssuedUploadView) -> IssuedUploadSchema:
        return cls.model_validate(view, from_attributes=True)
