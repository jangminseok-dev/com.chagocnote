from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class LookupCustomerQuery:
    ctx: ShopContext
    phone: str


@dataclass(frozen=True)
class LookupCustomerResult:
    """등록 1단계에서 '이미 등록된 번호예요 — 김민지(콩이, 두부)'를 보여 줄 만큼만. 번호는 담지 않는다."""

    customer_id: int
    name: str
    pet_names: list[str]
