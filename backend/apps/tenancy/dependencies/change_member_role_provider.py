from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.change_member_role_use_case import ChangeMemberRoleUseCase
from tenancy.app.use_cases.change_member_role_interactor import ChangeMemberRoleInteractor
from tenancy.dependencies.tenancy_wiring import build_invite_repository, build_member_repository


def get_change_member_role_use_case(db: DbSession) -> ChangeMemberRoleUseCase:
    return ChangeMemberRoleInteractor(
        members=build_member_repository(db), invites=build_invite_repository(db)
    )
