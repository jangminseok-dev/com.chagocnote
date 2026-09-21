from __future__ import annotations

from core.database import DbSession
from hub.app.ports.membership_directory_port import MembershipDirectoryPort
from tenancy.app.use_cases.list_memberships_interactor import ListMembershipsInteractor
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_list_memberships_use_case(db: DbSession) -> MembershipDirectoryPort:
    return ListMembershipsInteractor(members=build_member_repository(db))
