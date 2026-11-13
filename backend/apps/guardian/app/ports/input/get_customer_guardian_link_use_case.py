from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.get_customer_guardian_link_dto import CustomerGuardianLinkView, GetCustomerGuardianLinkQuery


class GetCustomerGuardianLinkUseCase(ABC):
    @abstractmethod
    async def get_link(self, query: GetCustomerGuardianLinkQuery) -> CustomerGuardianLinkView: ...
