from __future__ import annotations

from auth.app.use_cases.guard_active_user_interactor import GuardActiveUserInteractor
from auth.dependencies.auth_wiring import build_user_repository
from core.database import DbSession
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort


def get_guard_active_user_use_case(db: DbSession) -> ActiveUserGuardPort:
    return GuardActiveUserInteractor(users=build_user_repository(db))
