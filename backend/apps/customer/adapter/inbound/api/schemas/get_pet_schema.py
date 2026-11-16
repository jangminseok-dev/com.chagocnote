from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from customer.adapter.inbound.api.schemas.get_customer_schema import (
    CautionSchema,
    PetSchema,
    PetWithPhotoSchema,
)
from customer.app.dtos.customer_view_dto import PetDetailView, PetOverviewView


class OwnerSummarySchema(BaseModel):
    customer_id: int
    name: str
    phone_masked: str


class SiblingSchema(BaseModel):
    pet_id: int
    name: str
    species: str
    passed_away: bool


class PetDetailSchema(BaseModel):
    pet: PetSchema
    owner: OwnerSummarySchema
    siblings: list[SiblingSchema]
    caution: CautionSchema | None   # 보호자의 살아 있는 주의 표시(③-B)

    @classmethod
    def of(cls, view: PetDetailView) -> PetDetailSchema:
        return cls(
            pet=PetSchema.of(view.pet),
            owner=OwnerSummarySchema(
                customer_id=view.owner.customer_id, name=view.owner.name,
                phone_masked=view.owner.phone_masked,
            ),
            siblings=[
                SiblingSchema(pet_id=s.pet_id, name=s.name, species=s.species,
                              passed_away=s.passed_away)
                for s in view.siblings
            ],
            caution=(
                None if view.caution is None
                else CautionSchema(reason=view.caution.reason, until=view.caution.until)
            ),
        )


class PetRevisitSchema(BaseModel):
    """미용 주기와 다음 올 때(⑬ 설계 3.1) — 출처가 manual·computed 가 아니면 날짜는 매장의 기본 간격으로 어림이다."""

    cycle_weeks: int
    cycle_source: str               # manual · computed · single · none
    interval_count: int
    last_interval_weeks: int | None
    last_visit_date: date | None
    due_date: date | None
    estimated: bool
    has_upcoming: bool
    nudged_on: date | None          # 다시 올 때라고 안내한 날


class PetOverviewSchema(PetDetailSchema):
    """반려동물 상세(GET) — pet 에 프로필 사진을, 끝에 주기(⑬)를 더한다. 쓰기 응답은 사진 없는 PetDetailSchema 다."""

    pet: PetWithPhotoSchema
    revisit: PetRevisitSchema | None

    @classmethod
    def of_overview(cls, view: PetOverviewView) -> PetOverviewSchema:
        detail = PetDetailSchema.of(view.detail)
        r = view.revisit
        revisit = None if r is None else PetRevisitSchema(
            cycle_weeks=r.cycle_weeks, cycle_source=r.cycle_source, interval_count=r.interval_count,
            last_interval_weeks=r.last_interval_weeks, last_visit_date=r.last_visit_date, due_date=r.due_date,
            estimated=r.estimated, has_upcoming=r.has_upcoming, nudged_on=view.detail.pet.revisit_nudged_on,
        )
        return cls(pet=PetWithPhotoSchema.with_photo(view.detail.pet, view.photo), owner=detail.owner,
                   siblings=detail.siblings, caution=detail.caution, revisit=revisit)
