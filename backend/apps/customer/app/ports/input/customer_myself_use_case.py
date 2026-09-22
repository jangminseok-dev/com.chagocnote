from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery, CustomerMyselfResponse


class CustomerMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: CustomerMyselfQuery) -> CustomerMyselfResponse: ...
