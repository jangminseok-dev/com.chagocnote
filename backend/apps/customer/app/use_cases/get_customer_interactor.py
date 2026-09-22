from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class GetCustomerInteractor(GetCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def get_customer(self, query: GetCustomerQuery) -> CustomerDetailView:
        return await read_customer_detail(
            query.ctx, query.customer_id, self._customers, self._pets, self._today()
        )
