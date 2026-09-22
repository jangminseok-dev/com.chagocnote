from __future__ import annotations

from pydantic import BaseModel

from customer.adapter.inbound.api.schemas.get_customer_schema import PetSchema
from customer.app.dtos.customer_view_dto import PetDetailView


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
