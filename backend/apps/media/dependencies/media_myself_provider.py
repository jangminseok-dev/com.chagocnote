from __future__ import annotations

from media.adapter.outbound.log_media_myself_record_adapter import LogMediaMyselfRecordAdapter
from media.app.ports.input.media_myself_use_case import MediaMyselfUseCase
from media.app.use_cases.media_myself_interactor import MediaMyselfInteractor


def get_media_myself_use_case() -> MediaMyselfUseCase:
    return MediaMyselfInteractor(record=LogMediaMyselfRecordAdapter())
