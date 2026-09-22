from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery, LookupCustomerResult


class LookupCustomerUseCase(ABC):
    @abstractmethod
    async def lookup_customer(self, query: LookupCustomerQuery) -> LookupCustomerResult: ...
