from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.app.use_cases.remove_member_interactor import RemoveMemberInteractor
from tenancy.dependencies.tenancy_wiring import build_invite_repository, build_member_repository


def get_remove_member_use_case(db: DbSession) -> RemoveMemberUseCase:
    return RemoveMemberInteractor(
        members=build_member_repository(db), invites=build_invite_repository(db)
    )
