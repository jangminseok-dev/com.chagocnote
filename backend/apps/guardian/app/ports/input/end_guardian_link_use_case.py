from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.end_guardian_link_dto import EndGuardianLinkCommand


class EndGuardianLinkUseCase(ABC):
    @abstractmethod
    async def end_link(self, command: EndGuardianLinkCommand) -> None: ...
