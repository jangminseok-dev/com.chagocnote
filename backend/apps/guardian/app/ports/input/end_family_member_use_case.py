from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import EndFamilyMemberCommand


class EndFamilyMemberUseCase(ABC):
    @abstractmethod
    async def end_member(self, command: EndFamilyMemberCommand) -> None: ...
