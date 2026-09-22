from __future__ import annotations

from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery, LookupCustomerResult
from customer.app.ports.input.lookup_customer_use_case import LookupCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import CustomerNotFoundError
from customer.domain.services.phone_number import normalize_phone


class LookupCustomerInteractor(LookupCustomerUseCase):
    def __init__(self, customers: CustomerRepository, pets: PetRepository) -> None:
        self._customers = customers
        self._pets = pets

    async def lookup_customer(self, query: LookupCustomerQuery) -> LookupCustomerResult:
        customer = await self._customers.find_active_by_phone(query.ctx, normalize_phone(query.phone))
        if customer is None:
            raise CustomerNotFoundError("이 번호로 등록된 고객이 없습니다.")
        family = await self._pets.list_for_customers(query.ctx, [customer.id])
        return LookupCustomerResult(
            customer_id=customer.id,
            name=customer.name,
            pet_names=[pet.name for pet in family if not pet.passed_away],
        )
