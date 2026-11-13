from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.end_customer_guardian_link_dto import EndCustomerGuardianLinkCommand


class EndCustomerGuardianLinkUseCase(ABC):
    @abstractmethod
    async def end_link(self, command: EndCustomerGuardianLinkCommand) -> None: ...
