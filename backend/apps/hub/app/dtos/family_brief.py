from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CustomerBrief:
    """다른 스포크에 보여 줄 보호자 요약. 익명화한 고객이면 이름과 번호가 None 이다."""

    customer_id: int
    name: str | None
    phone_masked: str | None


@dataclass(frozen=True)
class PetBrief:
    """다른 스포크에 보여 줄 반려동물 요약. 보호자가 익명화됐으면 이름이 None 이다."""

    pet_id: int
    customer_id: int
    name: str | None
    species: str
    breed: str
    weight_kg: Decimal
    passed_away: bool


@dataclass(frozen=True)
class FamilyBriefs:
    """ID 로 찾는 요약 묶음. 이 매장에 없는 ID 는 빠진다."""

    customers: dict[int, CustomerBrief]
    pets: dict[int, PetBrief]
