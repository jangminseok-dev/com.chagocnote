from __future__ import annotations

from auth.app.use_cases.get_user_profiles_interactor import GetUserProfilesInteractor
from auth.dependencies.auth_wiring import build_user_repository
from core.database import DbSession
from hub.app.ports.user_directory_port import UserDirectoryPort


def get_get_user_profiles_use_case(db: DbSession) -> UserDirectoryPort:
    return GetUserProfilesInteractor(users=build_user_repository(db))
