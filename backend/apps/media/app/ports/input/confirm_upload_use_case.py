from __future__ import annotations

from abc import ABC, abstractmethod

from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.dtos.media_view_dto import MediaView


class ConfirmUploadUseCase(ABC):
    @abstractmethod
    async def confirm_upload(self, command: ConfirmUploadCommand) -> MediaView: ...
