from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from customer.app.dtos.customer_view_dto import (
    CustomerDetailView,
    CustomerOverviewView,
    CustomerView,
    PetView,
)


class ConditionSchema(BaseModel):
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


class CautionSchema(BaseModel):
    """살아 있는 주의 표시(③-B) — 매장용 응답에만 있다."""

    reason: str
    until: date


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
    grooming_consent_on: date | None

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
            grooming_consent_on=view.grooming_consent_on,
        )


class PetWithPhotoSchema(PetSchema):
    """조회 응답(고객 상세·반려동물 상세)의 반려동물 — 프로필 사진을 더한다."""

    photo: str | None   # 가장 최근 완료 기록의 대표 사진 썸네일 URL

    @classmethod
    def with_photo(cls, view: PetView, photo: str | None) -> PetWithPhotoSchema:
        return cls(**PetSchema.of(view).model_dump(), photo=photo)


def _caution(view) -> CautionSchema | None:
    return None if view is None else CautionSchema(reason=view.reason, until=view.until)


class CustomerSchema(BaseModel):
    customer_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None
    caution: CautionSchema | None

    @classmethod
    def of(cls, view: CustomerView) -> CustomerSchema:
        return cls(
            customer_id=view.customer_id, name=view.name, phone=view.phone,
            phone_alt=view.phone_alt, marketing_consent=view.marketing_consent,
            marketing_consent_changed_at=view.marketing_consent_changed_at, memo=view.memo,
            caution=_caution(view.caution),
        )


class CustomerDetailSchema(BaseModel):
    """고객 상세 — 전체 번호가 들어 있는 유일한 응답이다."""

    customer: CustomerSchema
    pets: list[PetSchema]

    @classmethod
    def of(cls, view: CustomerDetailView) -> CustomerDetailSchema:
        return cls(customer=CustomerSchema.of(view.customer), pets=[PetSchema.of(p) for p in view.pets])


class UpcomingVisitSchema(BaseModel):
    visit_id: int
    pet_id: int | None
    pet_name: str | None
    starts_at: datetime


class CustomerOverviewSchema(CustomerDetailSchema):
    """고객 상세(GET) — 방문 요약과 반려동물 프로필 사진을 더한다. 등록·수정 응답은 둘 다 없는 CustomerDetailSchema 다."""

    pets: list[PetWithPhotoSchema]
    no_show_count: int
    upcoming_visits: list[UpcomingVisitSchema]

    @classmethod
    def of(cls, view: CustomerOverviewView) -> CustomerOverviewSchema:
        return cls(
            customer=CustomerSchema.of(view.customer),
            pets=[PetWithPhotoSchema.with_photo(p, view.photos.get(p.pet_id)) for p in view.pets],
            no_show_count=view.no_show_count,
            upcoming_visits=[UpcomingVisitSchema.model_validate(u, from_attributes=True) for u in view.upcoming_visits],
        )
