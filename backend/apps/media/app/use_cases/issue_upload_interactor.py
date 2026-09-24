from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from media.app.dtos.issue_upload_dto import IssuedUploadView, IssueUploadCommand, UploadTargetsView
from media.app.ports.input.issue_upload_use_case import IssueUploadUseCase
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.services.media_rules import CONTENT_TYPE, check_upload
from media.domain.value_objects.new_media import NewMedia

PUT_VALID_FOR = timedelta(minutes=15)
_THUMB_TYPE = CONTENT_TYPE["photo"]   # 표시용·썸네일·영상 포스터는 모두 JPEG 다


class IssueUploadInteractor(IssueUploadUseCase):
    """행을 pending 으로 넣고 렌디션마다 PUT URL 을 서명한다. 서명은 계산이라 네트워크가 없다(설계 7.1)."""

    def __init__(self, media: MediaRepository, storage: ObjectStoragePort, now: Callable[[], datetime]) -> None:
        self._media = media
        self._storage = storage
        self._now = now

    async def issue_upload(self, command: IssueUploadCommand) -> IssuedUploadView:
        check_upload(command.kind, command.content_type, command.byte_size, command.width, command.height,
                     command.duration_seconds)
        media = await self._media.create(command.ctx, NewMedia(
            kind=command.kind, content_type=command.content_type, width=command.width, height=command.height,
            duration_seconds=command.duration_seconds, uploaded_by_member_id=command.ctx.member_id,
        ))
        seconds = int(PUT_VALID_FOR.total_seconds())
        keys = media.keys
        return IssuedUploadView(
            media_id=media.id,
            puts=UploadTargetsView(
                original=self._storage.presign_put(keys.original, command.content_type, seconds),
                display=self._storage.presign_put(keys.display, _THUMB_TYPE, seconds) if keys.display else None,
                thumb=self._storage.presign_put(keys.thumb, _THUMB_TYPE, seconds),
            ),
            expires_at=self._now() + PUT_VALID_FOR,
        )
