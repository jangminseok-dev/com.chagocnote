from __future__ import annotations

from tenancy.adapter.outbound.log_tenancy_myself_record_adapter import (
    LogTenancyMyselfRecordAdapter,
)
from tenancy.app.ports.input.tenancy_myself_use_case import TenancyMyselfUseCase
from tenancy.app.use_cases.tenancy_myself_interactor import TenancyMyselfInteractor


def get_tenancy_myself_use_case() -> TenancyMyselfUseCase:
    return TenancyMyselfInteractor(record=LogTenancyMyselfRecordAdapter())
