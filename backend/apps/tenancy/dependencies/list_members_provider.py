from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.user_directory_port import UserDirectoryPort
from tenancy.app.ports.input.list_members_use_case import ListMembersUseCase
from tenancy.app.use_cases.list_members_interactor import ListMembersInteractor
from tenancy.dependencies.hub_ports import get_user_directory
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_list_members_use_case(
    db: DbSession, users: UserDirectoryPort = Depends(get_user_directory)
) -> ListMembersUseCase:
    return ListMembersInteractor(members=build_member_repository(db), users=users)
