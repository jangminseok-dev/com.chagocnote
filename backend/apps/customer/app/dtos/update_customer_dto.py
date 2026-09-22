from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import CustomerInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateCustomerCommand:
    ctx: ShopContext
    customer_id: int
    customer: CustomerInput
