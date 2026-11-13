from __future__ import annotations

from fastapi import Depends

from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
from auth.app.use_cases.withdraw_interactor import WithdrawInteractor
from auth.dependencies.auth_wiring import (
    build_operator_repository,
    build_refresh_store,
    build_user_repository_with_cipher,
)
from auth.dependencies.hub_ports import get_guardian_lifecycle, get_membership_lifecycle
from core.database import DbSession
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort


def get_withdraw_use_case(
    db: DbSession, lifecycle: MembershipLifecyclePort = Depends(get_membership_lifecycle),
    guardians: GuardianLifecyclePort = Depends(get_guardian_lifecycle),
) -> WithdrawUseCase:
    return WithdrawInteractor(
        users=build_user_repository_with_cipher(db),
        operators=build_operator_repository(db),
        lifecycle=lifecycle,
        store=build_refresh_store(),
        guardians=guardians,
    )
