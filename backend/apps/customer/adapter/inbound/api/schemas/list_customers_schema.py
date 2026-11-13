from __future__ import annotations

from pydantic import BaseModel

from customer.app.dtos.list_customers_dto import CustomerListView


class PetSummarySchema(BaseModel):
    pet_id: int
    name: str
    species: str
    breed: str
    age_label: str
    has_conditions: bool
    passed_away: bool
    photo: str | None   # 프로필 사진 썸네일 URL


class FamilyCardSchema(BaseModel):
    customer_id: int
    name: str
    phone_masked: str
    pets: list[PetSummarySchema]
    caution: bool   # 살아 있는 주의 표시가 있다


class CustomerListSchema(BaseModel):
    """목록 — 번호는 가린 값만 들어 있다."""

    items: list[FamilyCardSchema]
    next_cursor: str | None
    pet_count: int

    @classmethod
    def of(cls, view: CustomerListView) -> CustomerListSchema:
        return cls(
            items=[
                FamilyCardSchema(
                    customer_id=card.customer_id, name=card.name, phone_masked=card.phone_masked,
                    pets=[
                        PetSummarySchema(
                            pet_id=p.pet_id, name=p.name, species=p.species, breed=p.breed,
                            age_label=p.age_label, has_conditions=p.has_conditions,
                            passed_away=p.passed_away, photo=p.photo,
                        )
                        for p in card.pets
                    ],
                    caution=card.caution,
                )
                for card in view.items
            ],
            next_cursor=view.next_cursor,
            pet_count=view.pet_count,
        )
