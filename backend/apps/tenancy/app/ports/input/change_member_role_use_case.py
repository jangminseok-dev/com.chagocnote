from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.change_member_role_dto import ChangedMember, ChangeMemberRoleCommand


class ChangeMemberRoleUseCase(ABC):
    @abstractmethod
    async def change_role(self, command: ChangeMemberRoleCommand) -> ChangedMember: ...
