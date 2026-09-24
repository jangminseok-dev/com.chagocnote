from __future__ import annotations

from pydantic import BaseModel

from media.app.dtos.media_view_dto import MediaView


class MediaSchema(BaseModel):
    media_id: int
    kind: str
    status: str
    size_bytes: int | None
    width: int
    height: int
    duration_seconds: int | None

    @classmethod
    def of(cls, view: MediaView) -> MediaSchema:
        return cls.model_validate(view, from_attributes=True)
