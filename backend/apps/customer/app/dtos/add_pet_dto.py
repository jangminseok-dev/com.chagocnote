from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import PetInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class AddPetCommand:
    ctx: ShopContext
    customer_id: int
    pet: PetInput
