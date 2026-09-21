from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.link_identity_dto import LinkedIdentities, LinkIdentityCommand


class LinkIdentityUseCase(ABC):
    @abstractmethod
    async def link(self, command: LinkIdentityCommand) -> LinkedIdentities: ...
