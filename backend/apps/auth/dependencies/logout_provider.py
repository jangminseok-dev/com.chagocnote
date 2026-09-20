from __future__ import annotations

from auth.app.ports.input.logout_use_case import LogoutUseCase
from auth.app.use_cases.logout_interactor import LogoutInteractor
from auth.dependencies.auth_wiring import build_refresh_store


def get_logout_use_case() -> LogoutUseCase:
    return LogoutInteractor(store=build_refresh_store())
