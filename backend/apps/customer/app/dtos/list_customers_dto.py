from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_search_dto import SortKey
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListCustomersQuery:
    ctx: ShopContext
    q: str | None
    sort: SortKey
    include_passed: bool
    cursor: str | None


@dataclass(frozen=True)
class PetSummaryView:
    pet_id: int
    name: str
    species: str
    breed: str
    age_label: str
    has_conditions: bool
    passed_away: bool
    photo: str | None   # 프로필 사진 썸네일 URL


@dataclass(frozen=True)
class FamilyCardView:
    """가족 카드 — 보호자 이름과 가린 번호, 그 아래 반려동물 줄."""

    customer_id: int
    name: str
    phone_masked: str
    pets: list[PetSummaryView]


@dataclass(frozen=True)
class CustomerListView:
    items: list[FamilyCardView]
    next_cursor: str | None
    pet_count: int
