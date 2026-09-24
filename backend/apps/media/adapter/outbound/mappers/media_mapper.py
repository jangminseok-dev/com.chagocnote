from __future__ import annotations

from media.adapter.outbound.orm.media_orm import MediaObjectOrm
from media.domain.entities.media_object import MediaObject
from media.domain.services.media_rules import MediaKeys


def to_media(orm: MediaObjectOrm) -> MediaObject:
    return MediaObject(
        id=orm.id, shop_id=orm.shop_id, kind=orm.kind, status=orm.status,
        keys=MediaKeys(original=orm.object_key, display=orm.display_key, thumb=orm.thumb_key),
        content_type=orm.content_type, size_bytes=orm.size_bytes, width=orm.width, height=orm.height,
        duration_seconds=orm.duration_seconds, uploaded_by_member_id=orm.uploaded_by_member_id,
        attached_at=orm.attached_at, created_at=orm.created_at, ready_at=orm.ready_at,
    )
