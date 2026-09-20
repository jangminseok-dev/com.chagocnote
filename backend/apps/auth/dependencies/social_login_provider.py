from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.dependencies.auth_wiring import (
    build_provider_resolver,
    build_session_issuer,
    build_user_repository,
)
from core.database import get_db


def get_social_login_use_case(db: AsyncSession = Depends(get_db)) -> SocialLoginUseCase:
    return SocialLoginInteractor(
        providers=build_provider_resolver(),
        users=build_user_repository(db),
        sessions=build_session_issuer(),
    )
