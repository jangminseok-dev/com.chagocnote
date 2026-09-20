from __future__ import annotations

from auth.adapter.outbound.log_auth_myself_record_adapter import LogAuthMyselfRecordAdapter
from auth.app.ports.input.auth_myself_use_case import AuthMyselfUseCase
from auth.app.use_cases.auth_myself_interactor import AuthMyselfInteractor


def get_auth_myself_use_case() -> AuthMyselfUseCase:
    return AuthMyselfInteractor(record=LogAuthMyselfRecordAdapter())
