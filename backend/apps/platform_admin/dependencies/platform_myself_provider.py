from __future__ import annotations

from platform_admin.adapter.outbound.log_platform_myself_record_adapter import (
    LogPlatformMyselfRecordAdapter,
)
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.app.use_cases.platform_myself_interactor import PlatformMyselfInteractor


def get_platform_myself_use_case() -> PlatformMyselfUseCase:
    return PlatformMyselfInteractor(record=LogPlatformMyselfRecordAdapter())
