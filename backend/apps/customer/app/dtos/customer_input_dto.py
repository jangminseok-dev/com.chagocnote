from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from customer.domain.value_objects.condition_entry import ConditionEntry
from customer.domain.value_objects.customer_profile import CustomerProfile
from customer.domain.value_objects.pet_profile import PetProfile


@dataclass(frozen=True)
class CustomerInput:
    """보호자 폼 전체. 문자열은 앞뒤 공백을 없앴고 빈 값은 None 이다(라우터가 바꿔 넣는다)."""

    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    memo: str | None

    def to_profile(self) -> CustomerProfile:
        return CustomerProfile.create(
            name=self.name, phone=self.phone, phone_alt=self.phone_alt,
            marketing_consent=self.marketing_consent, memo=self.memo,
        )


@dataclass(frozen=True)
class PetInput:
    """반려동물 폼 전체. 질병 목록은 통째로 온다."""

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

    def to_profile(self, known_condition_codes: frozenset[str], today: date) -> PetProfile:
        return PetProfile.create(
            name=self.name, species=self.species, breed=self.breed, sex=self.sex,
            neutered=self.neutered, birth_date=self.birth_date, birth_year=self.birth_year,
            weight_kg=self.weight_kg, no_known_conditions=self.no_known_conditions,
            memo=self.memo, conditions=self.conditions,
            known_condition_codes=known_condition_codes, today=today,
        )
