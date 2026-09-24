from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from media.app.ports.input.confirm_upload_use_case import ConfirmUploadUseCase
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.app.use_cases.confirm_upload_interactor import ConfirmUploadInteractor
from media.dependencies.media_wiring import build_media_repository, get_object_storage


def get_confirm_upload_use_case(
    db: DbSession, storage: ObjectStoragePort = Depends(get_object_storage)
) -> ConfirmUploadUseCase:
    return ConfirmUploadInteractor(media=build_media_repository(db), storage=storage)
