from __future__ import annotations

from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.app.use_cases.refresh_token_interactor import RefreshTokenInteractor
from auth.dependencies.auth_wiring import (
    build_refresh_store,
    build_session_issuer,
    build_user_repository,
)
from core.database import DbSession


def get_refresh_token_use_case(db: DbSession) -> RefreshTokenUseCase:
    return RefreshTokenInteractor(
        store=build_refresh_store(),
        users=build_user_repository(db),
        sessions=build_session_issuer(),
    )
