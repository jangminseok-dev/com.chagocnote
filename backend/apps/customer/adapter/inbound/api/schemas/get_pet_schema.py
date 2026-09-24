from __future__ import annotations

from pydantic import BaseModel

from customer.adapter.inbound.api.schemas.get_customer_schema import PetSchema, PetWithPhotoSchema
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
        )


class PetOverviewSchema(PetDetailSchema):
    """반려동물 상세(GET) — pet 에 프로필 사진을 더한다. 쓰기 응답은 사진 없는 PetDetailSchema 다."""

    pet: PetWithPhotoSchema

    @classmethod
    def of_overview(cls, view: PetOverviewView) -> PetOverviewSchema:
        detail = PetDetailSchema.of(view.detail)
        return cls(pet=PetWithPhotoSchema.with_photo(view.detail.pet, view.photo), owner=detail.owner,
                   siblings=detail.siblings)
