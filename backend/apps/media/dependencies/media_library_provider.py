from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.media_library_port import MediaLibraryPort
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.dependencies.media_wiring import build_media_repository, get_object_storage, utc_now


def get_media_library_use_case(
    db: DbSession, storage: ObjectStoragePort = Depends(get_object_storage)
) -> MediaLibraryPort:
    return MediaLibraryInteractor(media=build_media_repository(db), storage=storage, now=utc_now)
