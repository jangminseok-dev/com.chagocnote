from __future__ import annotations

from auth.app.use_cases.check_operator_interactor import CheckOperatorInteractor
from auth.dependencies.auth_wiring import build_operator_repository
from core.database import DbSession
from hub.app.ports.operator_directory_port import OperatorDirectoryPort


def get_check_operator_use_case(db: DbSession) -> OperatorDirectoryPort:
    return CheckOperatorInteractor(operators=build_operator_repository(db))
