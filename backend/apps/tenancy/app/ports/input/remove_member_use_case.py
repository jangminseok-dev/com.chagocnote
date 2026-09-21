from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand


class RemoveMemberUseCase(ABC):
    @abstractmethod
    async def remove(self, command: RemoveMemberCommand) -> None: ...
