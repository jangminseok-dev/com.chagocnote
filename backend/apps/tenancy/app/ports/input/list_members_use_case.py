from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.list_members_dto import ListMembersQuery, MemberView


class ListMembersUseCase(ABC):
    @abstractmethod
    async def list_members(self, query: ListMembersQuery) -> list[MemberView]: ...
