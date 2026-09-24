from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from media.app.ports.input.issue_upload_use_case import IssueUploadUseCase
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.app.use_cases.issue_upload_interactor import IssueUploadInteractor
from media.dependencies.media_wiring import build_media_repository, get_object_storage, utc_now


def get_issue_upload_use_case(
    db: DbSession, storage: ObjectStoragePort = Depends(get_object_storage)
) -> IssueUploadUseCase:
    return IssueUploadInteractor(media=build_media_repository(db), storage=storage, now=utc_now)
