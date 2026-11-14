from __future__ import annotations

from customer.adapter.outbound.orm.customer_orm import CustomerOrm, PetOrm
from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet, PetCondition


def to_customer(orm: CustomerOrm) -> Customer:
    """살아 있는 고객만 넘긴다 — 이름과 번호가 있다(CHECK 제약)."""
    return Customer(
        id=orm.id,
        shop_id=orm.shop_id,
        name=orm.name,
        phone=orm.phone,
        phone_alt=orm.phone_alt,
        marketing_consent=orm.marketing_consent,
        marketing_consent_changed_at=orm.marketing_consent_changed_at,
        memo=orm.memo,
        caution_reason=orm.caution_reason,
        caution_until=orm.caution_until,
    )


def to_pet(orm: PetOrm, conditions: list[PetCondition]) -> Pet:
    """살아 있는 고객의 반려동물만 넘긴다 — 이름이 있다."""
    return Pet(
        id=orm.id,
        customer_id=orm.customer_id,
        name=orm.name,
        species=orm.species,
        breed=orm.breed,
        sex=orm.sex,
        neutered=orm.neutered,
        birth_date=orm.birth_date,
        birth_year=orm.birth_year,
        weight_kg=orm.weight_kg,
        no_known_conditions=orm.no_known_conditions,
        memo=orm.memo,
        passed_away_at=orm.passed_away_at,
        conditions=tuple(conditions),
        grooming_consent_on=orm.grooming_consent_on,
    )
