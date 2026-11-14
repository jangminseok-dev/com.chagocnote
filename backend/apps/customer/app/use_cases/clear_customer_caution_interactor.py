from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.clear_customer_caution_dto import ClearCustomerCautionCommand
from customer.app.ports.input.clear_customer_caution_use_case import ClearCustomerCautionUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class ClearCustomerCautionInteractor(ClearCustomerCautionUseCase):
    """주의 표시를 푼다. 없던 것을 풀어도 된다(멱등)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def clear_customer_caution(self, command: ClearCustomerCautionCommand) -> CustomerDetailView:
        await self._customers.lock_active(command.ctx, command.customer_id)
        await self._customers.set_caution(command.ctx, command.customer_id, None, None, None)
        return await read_customer_detail(
            command.ctx, command.customer_id, self._customers, self._pets, self._today()
        )
