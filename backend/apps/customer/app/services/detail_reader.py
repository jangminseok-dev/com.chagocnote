"""고객 상세·반려동물 상세를 원본 표에서 읽어 조립한다. 여러 슬라이스가 쓰기를 마친 뒤 같은 모양으로 돌려준다."""
from __future__ import annotations

from datetime import date

from customer.app.dtos.customer_view_dto import (
    CustomerDetailView,
    CustomerView,
    OwnerSummaryView,
    PetDetailView,
    PetView,
    SiblingView,
)
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from hub.app.dtos.shop_context import ShopContext


async def read_customer_detail(
    ctx: ShopContext, customer_id: int, customers: CustomerRepository, pets: PetRepository,
    today: date,
) -> CustomerDetailView:
    customer = await customers.get_active(ctx, customer_id)
    family = await pets.list_for_customers(ctx, [customer_id])
    return CustomerDetailView(
        customer=CustomerView.of(customer), pets=[PetView.of(pet, today) for pet in family]
    )


async def read_pet_detail(
    ctx: ShopContext, pet_id: int, customers: CustomerRepository, pets: PetRepository, today: date
) -> PetDetailView:
    pet = await pets.get(ctx, pet_id)
    owner = await customers.get_active(ctx, pet.customer_id)
    family = await pets.list_for_customers(ctx, [pet.customer_id])
    return PetDetailView(
        pet=PetView.of(pet, today),
        owner=OwnerSummaryView.of(owner),
        siblings=[
            SiblingView(pet_id=p.id, name=p.name, species=p.species, passed_away=p.passed_away)
            for p in family if p.id != pet.id
        ],
    )
