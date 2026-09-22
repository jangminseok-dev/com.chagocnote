from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.update_customer_dto import UpdateCustomerCommand
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class UpdateCustomerInteractor(UpdateCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def update_customer(self, command: UpdateCustomerCommand) -> CustomerDetailView:
        profile = command.customer.to_profile()
        # 고객 행을 잠근 뒤 다시 읽는다. 익명화와 겹치면 익명화가 끝난 뒤 404 가 된다.
        current = await self._customers.lock_active(command.ctx, command.customer_id)
        await self._customers.update(
            command.ctx, command.customer_id, profile,
            consent_changed=current.marketing_consent != profile.marketing_consent,
        )
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)
        return await read_customer_detail(
            command.ctx, command.customer_id, self._customers, self._pets, self._today()
        )
