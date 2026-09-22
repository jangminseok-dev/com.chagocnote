from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class RegisterCustomerInteractor(RegisterCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today

    async def register_customer(self, command: RegisterCustomerCommand) -> CustomerDetailView:
        # 쓰기 전에 두 폼을 모두 검증한다. 번호 중복은 유일 색인이 막는다(동시에 두 번 와도 하나만 성공).
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        customer_profile = command.customer.to_profile()
        pet_profile = command.pet.to_profile(codes, self._today())
        customer = await self._customers.create(command.ctx, customer_profile)
        await self._pets.add(command.ctx, customer.id, pet_profile)
        await self._search.rebuild_search_entry(command.ctx, customer.id)
        return await read_customer_detail(
            command.ctx, customer.id, self._customers, self._pets, self._today()
        )
