from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from customer.domain.services.pet_age import check_birth
from customer.domain.services.pet_health import check_conditions
from customer.domain.value_objects.condition_entry import ConditionEntry


@dataclass(frozen=True)
class PetProfile:
    """검증을 마친 반려동물 정보. 나이 규칙과 질병 규칙을 통과했다."""

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
    conditions: tuple[ConditionEntry, ...]

    @classmethod
    def create(
        cls, *, name: str, species: str, breed: str, sex: str, neutered: bool,
        birth_date: date | None, birth_year: int | None, weight_kg: Decimal,
        no_known_conditions: bool, memo: str | None, conditions: tuple[ConditionEntry, ...],
        known_condition_codes: frozenset[str], today: date,
    ) -> PetProfile:
        check_birth(birth_date, birth_year, today)
        check_conditions(conditions, no_known_conditions, known_condition_codes)
        return cls(
            name=name, species=species, breed=breed, sex=sex, neutered=neutered,
            birth_date=birth_date, birth_year=birth_year, weight_kg=weight_kg,
            no_known_conditions=no_known_conditions, memo=memo, conditions=conditions,
        )
