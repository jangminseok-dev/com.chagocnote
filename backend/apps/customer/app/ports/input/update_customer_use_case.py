from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.update_customer_dto import UpdateCustomerCommand


class UpdateCustomerUseCase(ABC):
    @abstractmethod
    async def update_customer(self, command: UpdateCustomerCommand) -> CustomerDetailView: ...
