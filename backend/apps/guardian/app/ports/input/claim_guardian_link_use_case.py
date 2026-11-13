from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.claim_guardian_link_dto import ClaimGuardianLinkCommand, ClaimGuardianLinkResult


class ClaimGuardianLinkUseCase(ABC):
    @abstractmethod
    async def claim(self, command: ClaimGuardianLinkCommand) -> ClaimGuardianLinkResult: ...
