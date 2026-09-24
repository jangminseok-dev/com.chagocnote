from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.media_urls import MediaUrls
from hub.app.dtos.shop_context import ShopContext
from hub.app.errors import MediaClaimAlreadyAttachedError, MediaClaimNotFoundError, MediaClaimNotReadyError
from hub.app.ports.media_library_port import MediaLibraryPort
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.services.url_expiry import signing_window


class MediaLibraryInteractor(MediaLibraryPort):
    """허브의 MediaLibraryPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(self, media: MediaRepository, storage: ObjectStoragePort, now: Callable[[], datetime]) -> None:
        self._media = media
        self._storage = storage
        self._now = now

    async def claim(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str]:
        if not media_ids:
            return {}
        claimed = await self._media.attach_all(ctx, media_ids)
        if claimed is not None:
            return claimed
        # 왜 못 가져갔는지는 가져가기를 되돌린 뒤 읽어서 가린다 — 없는 것 → 준비 전 → 이미 붙음 순서.
        found = {m.id: m for m in await self._media.list(ctx, media_ids)}
        if any(media_id not in found for media_id in media_ids):
            raise MediaClaimNotFoundError("사진·영상을 찾을 수 없습니다.")
        if any(not m.ready for m in found.values()):
            raise MediaClaimNotReadyError("아직 올리는 중인 사진·영상입니다.")
        raise MediaClaimAlreadyAttachedError("이미 다른 기록에 붙은 사진·영상입니다.")

    async def release(self, ctx: ShopContext, media_ids: list[int]) -> None:
        if media_ids:
            await self._media.detach(ctx, media_ids)

    async def read_urls(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, MediaUrls]:
        if not media_ids:
            return {}
        window = signing_window(self._now(), ctx.timezone)
        sign = self._storage.presign_get
        return {
            m.id: MediaUrls(
                media_id=m.id, kind=m.kind, original_url=sign(m.keys.original, window),
                display_url=sign(m.keys.display, window) if m.keys.display else None,
                thumb_url=sign(m.keys.thumb, window), width=m.width, height=m.height,
                duration_seconds=m.duration_seconds,
            )
            for m in await self._media.list(ctx, media_ids) if m.ready
        }
