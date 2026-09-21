from __future__ import annotations

from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
from auth.app.use_cases.link_identity_interactor import LinkIdentityInteractor
from auth.dependencies.auth_wiring import build_provider_resolver, build_user_repository_with_cipher
from core.database import DbSession


def get_link_identity_use_case(db: DbSession) -> LinkIdentityUseCase:
    return LinkIdentityInteractor(
        providers=build_provider_resolver(), users=build_user_repository_with_cipher(db)
    )
