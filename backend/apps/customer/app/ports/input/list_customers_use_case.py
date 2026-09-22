from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.list_customers_dto import CustomerListView, ListCustomersQuery


class ListCustomersUseCase(ABC):
    @abstractmethod
    async def list_customers(self, query: ListCustomersQuery) -> CustomerListView: ...
