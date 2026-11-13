from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.list_guardian_links_dto import GuardianLinkView, ListGuardianLinksQuery


class ListGuardianLinksUseCase(ABC):
    @abstractmethod
    async def list_links(self, query: ListGuardianLinksQuery) -> list[GuardianLinkView]: ...
