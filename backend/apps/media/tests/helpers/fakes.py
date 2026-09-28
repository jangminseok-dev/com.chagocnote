"""media 인터랙터 테스트용 메모리 스텁. 스텁은 포트 ABC 를 상속한다(`apps/media/tests/test_fakes_are_ports.py`)."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.entities.media_object import PENDING, READY, MediaObject
from media.domain.errors import MediaNotFoundError
from media.domain.services.media_rules import object_keys
from media.domain.value_objects.object_info import ObjectInfo

NOW = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeMedia(MediaRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, MediaObject] = {}
        self._next = 1

    def seed(self, shop_id=1, kind="photo", status=PENDING, **fields) -> MediaObject:
        media = MediaObject(
            id=self._next, shop_id=shop_id, kind=kind, status=status, keys=object_keys(shop_id, self._next, kind),
            content_type="image/jpeg" if kind == "photo" else "video/mp4",
            size_bytes=1000 if status == READY else None, width=3000, height=2000,
            duration_seconds=None if kind == "photo" else 30, uploaded_by_member_id=11, attached_at=None,
            created_at=NOW, ready_at=NOW if status == READY else None,
        )
        media = replace(media, **fields)
        self.rows[media.id] = media
        self._next += 1
        return media

    async def create(self, ctx, new):
        media = self.seed(shop_id=ctx.shop_id, kind=new.kind, content_type=new.content_type, width=new.width,
                          height=new.height, duration_seconds=new.duration_seconds,
                          uploaded_by_member_id=new.uploaded_by_member_id)
        self.journal.append(("create_media", media.id))
        return media

    async def get(self, ctx, media_id):
        media = self.rows.get(media_id)
        if media is None or media.shop_id != ctx.shop_id:
            raise MediaNotFoundError("사진·영상을 찾을 수 없습니다.")
        return media

    async def mark_ready(self, ctx, media_id, size_bytes):
        media = await self.get(ctx, media_id)
        if media.status != PENDING:
            return False
        self.rows[media_id] = replace(media, status=READY, size_bytes=size_bytes, ready_at=NOW)
        self.journal.append(("mark_ready", media_id, size_bytes))
        return True

    async def attach_all(self, ctx, media_ids):
        mine = [self.rows.get(i) for i in set(media_ids)]
        if any(m is None or m.shop_id != ctx.shop_id or not m.ready or m.attached_at for m in mine):
            return None
        for m in mine:
            self.rows[m.id] = replace(m, attached_at=NOW)
        self.journal.append(("attach", sorted(media_ids)))
        return {m.id: m.kind for m in mine}

    async def detach(self, ctx, media_ids):
        for i in media_ids:
            if i in self.rows and self.rows[i].shop_id == ctx.shop_id:
                self.rows[i] = replace(self.rows[i], attached_at=None)
        self.journal.append(("detach", sorted(media_ids)))

    async def list(self, ctx, media_ids):
        return [m for i, m in sorted(self.rows.items()) if i in media_ids and m.shop_id == ctx.shop_id]


class FakeStorage(ObjectStoragePort):
    """객체는 {키: ObjectInfo}. 서명 URL 은 키와 형식이 보이는 가짜 문자열이다."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.objects: dict[str, ObjectInfo] = {}

    def put(self, key: str, size_bytes: int = 1000, content_type: str = "image/jpeg") -> None:
        self.objects[key] = ObjectInfo(size_bytes=size_bytes, content_type=content_type)

    def presign_put(self, key, content_type, expires_in_seconds):
        return f"put://{key}?type={content_type}&expires={expires_in_seconds}"

    def presign_get(self, key, window, download_as=None):
        download = f"&download={download_as}" if download_as else ""
        return f"get://{key}?signed={window.signed_at:%Y%m%dT%H%M}{download}"

    async def head(self, key):
        self.journal.append(("head", key))
        return self.objects.get(key)

    async def delete(self, keys):
        self.journal.append(("delete", tuple(keys)))
        for key in keys:
            self.objects.pop(key, None)
