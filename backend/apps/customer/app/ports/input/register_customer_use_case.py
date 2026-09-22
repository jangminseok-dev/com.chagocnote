from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand


class RegisterCustomerUseCase(ABC):
    @abstractmethod
    async def register_customer(self, command: RegisterCustomerCommand) -> CustomerDetailView: ...
