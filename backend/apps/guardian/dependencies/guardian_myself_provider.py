from __future__ import annotations

from guardian.adapter.outbound.log_guardian_myself_record_adapter import (
    LogGuardianMyselfRecordAdapter,
)
from guardian.app.ports.input.guardian_myself_use_case import GuardianMyselfUseCase
from guardian.app.use_cases.guardian_myself_interactor import GuardianMyselfInteractor


def get_guardian_myself_use_case() -> GuardianMyselfUseCase:
    return GuardianMyselfInteractor(record=LogGuardianMyselfRecordAdapter())
