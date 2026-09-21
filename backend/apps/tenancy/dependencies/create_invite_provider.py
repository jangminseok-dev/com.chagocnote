from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.app.use_cases.create_invite_interactor import CreateInviteInteractor
from tenancy.dependencies.tenancy_wiring import build_invite_repository


def get_create_invite_use_case(db: DbSession) -> CreateInviteUseCase:
    return CreateInviteInteractor(invites=build_invite_repository(db))
