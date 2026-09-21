from __future__ import annotations

from core.database import DbSession
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort
from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tenancy.dependencies.tenancy_wiring import (
    build_invite_repository,
    build_member_repository,
    build_shop_repository,
)


def get_apply_withdrawal_use_case(db: DbSession) -> MembershipLifecyclePort:
    return ApplyWithdrawalInteractor(
        members=build_member_repository(db),
        shops=build_shop_repository(db),
        invites=build_invite_repository(db),
    )
