from __future__ import annotations

from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.dtos.media_view_dto import MediaView
from media.app.ports.input.confirm_upload_use_case import ConfirmUploadUseCase
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.errors import MediaNotUploadedError, MediaTooLargeError, MediaTypeUnsupportedError
from media.domain.services.media_rules import CONTENT_TYPE, PHOTO, check_size


class ConfirmUploadInteractor(ConfirmUploadUseCase):
    """객체마다 HEAD 로 존재·크기·형식을 대조하고 pending → ready 로 바꾼다(설계 7.1).

    HEAD 는 행을 잠그지 않은 채 한다(외부 네트워크). 같은 매장 멤버면 발급자가 아니어도 확인할 수 있다.
    이미 ready 면 그대로 돌려준다 — 앱이 응답을 못 받고 다시 불러도, 두 기기가 동시에 불러도 결과가 같다(M13).
    """

    def __init__(self, media: MediaRepository, storage: ObjectStoragePort) -> None:
        self._media = media
        self._storage = storage

    async def confirm_upload(self, command: ConfirmUploadCommand) -> MediaView:
        ctx = command.ctx
        media = await self._media.get(ctx, command.media_id)
        if media.ready:
            return MediaView.of(media)
        keys = media.keys
        found = {key: await self._storage.head(key) for key in keys.all()}
        if any(info is None for info in found.values()):
            raise MediaNotUploadedError("아직 다 올라오지 않았습니다. 올린 뒤 다시 확인해 주세요.")
        expected = {key: CONTENT_TYPE[PHOTO] for key in keys.all()} | {keys.original: media.content_type}
        try:
            for key, info in found.items():
                if info.content_type != expected[key]:
                    raise MediaTypeUnsupportedError("선언한 형식과 다른 파일이 올라왔습니다.")
                check_size(media.kind if key == keys.original else PHOTO, info.size_bytes)
        except (MediaTypeUnsupportedError, MediaTooLargeError):
            await self._storage.delete(list(keys.all()))   # 받지 않는 파일은 남기지 않는다
            raise
        await self._media.mark_ready(ctx, media.id, found[keys.original].size_bytes)
        return MediaView.of(await self._media.get(ctx, media.id))
