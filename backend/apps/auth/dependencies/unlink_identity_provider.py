from __future__ import annotations

from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
from auth.app.use_cases.unlink_identity_interactor import UnlinkIdentityInteractor
from auth.dependencies.auth_wiring import (
    build_refresh_store,
    build_session_issuer,
    build_user_repository_with_cipher,
)
from core.database import DbSession


def get_unlink_identity_use_case(db: DbSession) -> UnlinkIdentityUseCase:
    return UnlinkIdentityInteractor(
        users=build_user_repository_with_cipher(db),
        store=build_refresh_store(),
        sessions=build_session_issuer(),
    )
