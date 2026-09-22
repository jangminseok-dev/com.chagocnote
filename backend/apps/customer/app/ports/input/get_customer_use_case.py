from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.get_customer_dto import GetCustomerQuery


class GetCustomerUseCase(ABC):
    @abstractmethod
    async def get_customer(self, query: GetCustomerQuery) -> CustomerDetailView: ...
