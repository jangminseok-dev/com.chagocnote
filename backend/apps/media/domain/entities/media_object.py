from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from media.domain.services.media_rules import MediaKeys

PENDING = "pending"
READY = "ready"


@dataclass(frozen=True)
class MediaObject:
    """저장소에 올리는 사진·영상 하나. 발급 때 pending 으로 생기고, 객체가 다 올라온 것을 확인하면 ready 다.

    기록(visit)이 가져가면 attached_at 이 찍힌다. 어느 기록인지는 visit 이 안다(media 는 visit 을 모른다).
    """

    id: int
    shop_id: int
    kind: str
    status: str
    keys: MediaKeys
    content_type: str
    size_bytes: int | None
    width: int
    height: int
    duration_seconds: int | None
    uploaded_by_member_id: int
    attached_at: datetime | None
    created_at: datetime
    ready_at: datetime | None

    @property
    def ready(self) -> bool:
        return self.status == READY
