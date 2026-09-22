from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand


class DeleteCustomerUseCase(ABC):
    @abstractmethod
    async def delete_customer(self, command: DeleteCustomerCommand) -> None: ...
