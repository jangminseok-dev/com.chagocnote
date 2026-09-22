from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from customer.app.dtos.customer_view_dto import CustomerDetailView, CustomerView, PetView


class ConditionSchema(BaseModel):
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


class PetSchema(BaseModel):
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
    weight_kg: float
    no_known_conditions: bool
    has_conditions: bool
    conditions: list[ConditionSchema]
    memo: str | None
    passed_away_at: datetime | None

    @classmethod
    def of(cls, view: PetView) -> PetSchema:
        return cls(
            pet_id=view.pet_id, customer_id=view.customer_id, name=view.name,
            species=view.species, breed=view.breed, sex=view.sex, neutered=view.neutered,
            birth_date=view.birth_date, birth_year=view.birth_year, age_label=view.age_label,
            weight_kg=float(view.weight_kg), no_known_conditions=view.no_known_conditions,
            has_conditions=view.has_conditions,
            conditions=[
                ConditionSchema(type_code=c.type_code, label=c.label,
                                custom_label=c.custom_label, note=c.note)
                for c in view.conditions
            ],
            memo=view.memo, passed_away_at=view.passed_away_at,
        )


class CustomerSchema(BaseModel):
    customer_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None

    @classmethod
    def of(cls, view: CustomerView) -> CustomerSchema:
        return cls(
            customer_id=view.customer_id, name=view.name, phone=view.phone,
            phone_alt=view.phone_alt, marketing_consent=view.marketing_consent,
            marketing_consent_changed_at=view.marketing_consent_changed_at, memo=view.memo,
        )


class CustomerDetailSchema(BaseModel):
    """고객 상세 — 전체 번호가 들어 있는 유일한 응답이다."""

    customer: CustomerSchema
    pets: list[PetSchema]

    @classmethod
    def of(cls, view: CustomerDetailView) -> CustomerDetailSchema:
        return cls(customer=CustomerSchema.of(view.customer), pets=[PetSchema.of(p) for p in view.pets])
