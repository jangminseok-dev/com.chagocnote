from __future__ import annotations

from fastapi import Depends

from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.dependencies.auth_wiring import build_user_repository
from auth.dependencies.hub_ports import get_membership_directory
from core.database import DbSession
from hub.app.ports.membership_directory_port import MembershipDirectoryPort


def get_get_me_use_case(
    db: DbSession, memberships: MembershipDirectoryPort = Depends(get_membership_directory)
) -> GetMeUseCase:
    return GetMeInteractor(users=build_user_repository(db), memberships=memberships)
