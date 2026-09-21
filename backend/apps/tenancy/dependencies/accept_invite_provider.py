from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.dependencies.hub_ports import get_active_user_guard
from tenancy.dependencies.tenancy_wiring import (
    build_invite_attempt_limiter,
    build_invite_repository,
    build_member_repository,
    build_shop_repository,
)


def get_accept_invite_use_case(
    db: DbSession, users: ActiveUserGuardPort = Depends(get_active_user_guard)
) -> AcceptInviteUseCase:
    return AcceptInviteInteractor(
        invites=build_invite_repository(db),
        members=build_member_repository(db),
        shops=build_shop_repository(db),
        limiter=build_invite_attempt_limiter(),
        users=users,
    )
