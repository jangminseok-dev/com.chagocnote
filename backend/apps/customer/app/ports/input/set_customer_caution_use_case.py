from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.set_customer_caution_dto import SetCustomerCautionCommand


class SetCustomerCautionUseCase(ABC):
    @abstractmethod
    async def set_customer_caution(self, command: SetCustomerCautionCommand) -> CustomerDetailView: ...
