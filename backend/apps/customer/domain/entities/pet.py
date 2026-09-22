from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class PetCondition:
    """반려동물이 가진 질병 한 항목. label 은 정해진 종류의 이름이다(기타면 '기타')."""

    type_code: str
    label: str
    custom_label: str | None
    note: str | None


@dataclass(frozen=True)
class Pet:
    id: int
    customer_id: int
    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    weight_kg: Decimal
    no_known_conditions: bool
    memo: str | None
    passed_away_at: datetime | None
    conditions: tuple[PetCondition, ...]

    @property
    def has_conditions(self) -> bool:
        return bool(self.conditions)

    @property
    def passed_away(self) -> bool:
        return self.passed_away_at is not None
