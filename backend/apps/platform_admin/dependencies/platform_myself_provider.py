from __future__ import annotations

from fastapi import Depends

from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from platform_admin.adapter.outbound.log_platform_myself_record_adapter import (
    LogPlatformMyselfRecordAdapter,
)
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.app.use_cases.platform_myself_interactor import PlatformMyselfInteractor
from platform_admin.dependencies.hub_ports import get_operator_directory


def get_platform_myself_use_case(
    operators: OperatorDirectoryPort = Depends(get_operator_directory),
) -> PlatformMyselfUseCase:
    return PlatformMyselfInteractor(record=LogPlatformMyselfRecordAdapter(), operators=operators)
