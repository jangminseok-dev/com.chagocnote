from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.clear_customer_caution_dto import ClearCustomerCautionCommand


class ClearCustomerCautionUseCase(ABC):
    @abstractmethod
    async def clear_customer_caution(self, command: ClearCustomerCautionCommand) -> CustomerDetailView: ...
