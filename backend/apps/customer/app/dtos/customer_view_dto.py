from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet
from customer.domain.services.pet_age import age_label
from customer.domain.services.phone_number import mask_phone


@dataclass(frozen=True)
class ConditionView:
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


@dataclass(frozen=True)
class PetView:
    pet_id: int
    customer_id: int
    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    age_label: str
    weight_kg: Decimal
    no_known_conditions: bool
    has_conditions: bool
    conditions: list[ConditionView]
    memo: str | None
    passed_away_at: datetime | None

    @classmethod
    def of(cls, pet: Pet, today: date) -> PetView:
        return cls(
            pet_id=pet.id, customer_id=pet.customer_id, name=pet.name, species=pet.species,
            breed=pet.breed, sex=pet.sex, neutered=pet.neutered, birth_date=pet.birth_date,
            birth_year=pet.birth_year, age_label=age_label(pet.birth_date, pet.birth_year, today),
            weight_kg=pet.weight_kg, no_known_conditions=pet.no_known_conditions,
            has_conditions=pet.has_conditions,
            conditions=[
                ConditionView(type_code=c.type_code, label=c.label, custom_label=c.custom_label,
                              note=c.note)
                for c in pet.conditions
            ],
            memo=pet.memo, passed_away_at=pet.passed_away_at,
        )


@dataclass(frozen=True)
class CustomerView:
    """보호자 전체 — 전체 번호가 들어 있다. 고객 상세에서만 내보낸다."""

    customer_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None

    @classmethod
    def of(cls, customer: Customer) -> CustomerView:
        return cls(
            customer_id=customer.id, name=customer.name, phone=customer.phone,
            phone_alt=customer.phone_alt, marketing_consent=customer.marketing_consent,
            marketing_consent_changed_at=customer.marketing_consent_changed_at, memo=customer.memo,
        )


@dataclass(frozen=True)
class CustomerDetailView:
    customer: CustomerView
    pets: list[PetView]


@dataclass(frozen=True)
class OwnerSummaryView:
    """반려동물 화면의 보호자 요약. 번호는 가린다 — 전체 번호는 고객 상세에서만 준다."""

    customer_id: int
    name: str
    phone_masked: str

    @classmethod
    def of(cls, customer: Customer) -> OwnerSummaryView:
        return cls(customer_id=customer.id, name=customer.name, phone_masked=mask_phone(customer.phone))


@dataclass(frozen=True)
class SiblingView:
    pet_id: int
    name: str
    species: str
    passed_away: bool


@dataclass(frozen=True)
class PetDetailView:
    pet: PetView
    owner: OwnerSummaryView
    siblings: list[SiblingView]
