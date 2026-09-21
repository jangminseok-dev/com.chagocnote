from __future__ import annotations

from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.dependencies.auth_wiring import (
    build_provider_resolver,
    build_session_issuer,
    build_user_repository_with_cipher,
)
from core.database import DbSession


def get_social_login_use_case(db: DbSession) -> SocialLoginUseCase:
    return SocialLoginInteractor(
        providers=build_provider_resolver(),
        users=build_user_repository_with_cipher(db),
        sessions=build_session_issuer(),
    )
