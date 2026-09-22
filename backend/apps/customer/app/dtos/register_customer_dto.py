from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import CustomerInput, PetInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RegisterCustomerCommand:
    """보호자와 첫 반려동물을 한 번에 등록한다."""

    ctx: ShopContext
    customer: CustomerInput
    pet: PetInput
