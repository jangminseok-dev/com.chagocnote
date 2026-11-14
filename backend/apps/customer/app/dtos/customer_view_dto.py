from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet
from customer.domain.services.care_marks import caution_active
from customer.domain.services.pet_age import age_label
from customer.domain.services.phone_number import mask_phone


@dataclass(frozen=True)
class ConditionView:
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


@dataclass(frozen=True)
class CautionView:
    """살아 있는 주의 표시(③-B). 기한이 지난 것은 뷰가 되지 않는다."""

    reason: str
    until: date

    @classmethod
    def of(cls, customer: Customer, today: date) -> CautionView | None:
        if customer.caution_reason is None or not caution_active(customer.caution_until, today):
            return None
        return cls(reason=customer.caution_reason, until=customer.caution_until)


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
    grooming_consent_on: date | None = None   # 미용 동의를 받은 날(③-B)

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
            grooming_consent_on=pet.grooming_consent_on,
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
    caution: CautionView | None = None

    @classmethod
    def of(cls, customer: Customer, today: date) -> CustomerView:
        return cls(
            customer_id=customer.id, name=customer.name, phone=customer.phone,
            phone_alt=customer.phone_alt, marketing_consent=customer.marketing_consent,
            marketing_consent_changed_at=customer.marketing_consent_changed_at, memo=customer.memo,
            caution=CautionView.of(customer, today),
        )


@dataclass(frozen=True)
class CustomerDetailView:
    customer: CustomerView
    pets: list[PetView]


@dataclass(frozen=True)
class UpcomingVisitView:
    visit_id: int
    pet_id: int | None      # None 이면 보호자만의 방문
    pet_name: str | None
    starts_at: datetime     # 매장 시간대


@dataclass(frozen=True)
class CustomerOverviewView:
    """고객 상세 화면 — 보호자·반려동물에 방문 요약(노쇼 횟수, 다가오는 예약)을 더한다."""

    customer: CustomerView
    pets: list[PetView]
    no_show_count: int
    upcoming_visits: list[UpcomingVisitView]
    photos: dict[int, str]   # 반려동물 ID → 프로필 사진 썸네일 URL(사진이 없는 아이는 빠진다)


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
    caution: CautionView | None = None   # 보호자의 살아 있는 주의 표시 — [보호자] 탭이 이 응답으로 그린다


@dataclass(frozen=True)
class PetOverviewView:
    """반려동물 상세 화면(GET) — 상세에 프로필 사진을 더한다. 쓰기 응답은 사진 없는 PetDetailView 다."""

    detail: PetDetailView
    photo: str | None
