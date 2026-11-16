from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import PetInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdatePetCommand:
    ctx: ShopContext
    pet_id: int
    pet: PetInput
    intake_answer_id: int | None = None   # 이 답으로 등록·반영한다 — 같은 트랜잭션에서 답을 지운다(⑪-C)
