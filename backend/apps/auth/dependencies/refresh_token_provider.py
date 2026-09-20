from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.app.use_cases.refresh_token_interactor import RefreshTokenInteractor
from auth.dependencies.auth_wiring import (
    build_refresh_store,
    build_session_issuer,
    build_user_repository,
)
from core.database import get_db


def get_refresh_token_use_case(db: AsyncSession = Depends(get_db)) -> RefreshTokenUseCase:
    return RefreshTokenInteractor(
        store=build_refresh_store(),
        users=build_user_repository(db),
        sessions=build_session_issuer(),
    )
