from __future__ import annotations

from dataclasses import dataclass

from media.domain.entities.media_object import MediaObject


@dataclass(frozen=True)
class MediaView:
    media_id: int
    kind: str
    status: str
    size_bytes: int | None
    width: int
    height: int
    duration_seconds: int | None

    @classmethod
    def of(cls, media: MediaObject) -> MediaView:
        return cls(media_id=media.id, kind=media.kind, status=media.status, size_bytes=media.size_bytes,
                   width=media.width, height=media.height, duration_seconds=media.duration_seconds)
