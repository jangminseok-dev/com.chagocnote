from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from hub.app.dtos.family_brief import FamilyBriefs
from visit.domain.entities.visit import Visit


@dataclass(frozen=True)
class MenuBriefView:
    menu_id: int
    name: str


@dataclass(frozen=True)
class CustomerBriefView:
    """익명화한 고객이면 이름과 번호가 None 이다 — 앱은 '삭제된 고객'으로 보인다."""

    customer_id: int
    name: str | None
    phone_masked: str | None


@dataclass(frozen=True)
class PetBriefView:
    pet_id: int
    name: str | None
    species: str
    breed: str
    weight_kg: Decimal


@dataclass(frozen=True)
class VisitView:
    """방문 하나. 시각은 모두 매장 시간대로 바꿔 내보낸다."""

    visit_id: int
    customer: CustomerBriefView
    pet: PetBriefView | None
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    cancel_reason: str | None
    memo: str | None
    menus: list[MenuBriefView]
    status_changed_by_member_id: int | None

    @classmethod
    def of(cls, visit: Visit, briefs: FamilyBriefs, menu_names: dict[int, str], zone: ZoneInfo) -> VisitView:
        def local(moment: datetime | None) -> datetime | None:
            return moment.astimezone(zone) if moment is not None else None

        customer = briefs.customers.get(visit.customer_id)
        pet = briefs.pets.get(visit.pet_id) if visit.pet_id is not None else None
        return cls(
            visit_id=visit.id,
            customer=CustomerBriefView(
                customer_id=visit.customer_id,
                name=customer.name if customer else None,
                phone_masked=customer.phone_masked if customer else None,
            ),
            pet=PetBriefView(pet_id=pet.pet_id, name=pet.name, species=pet.species, breed=pet.breed,
                             weight_kg=pet.weight_kg) if pet else None,
            starts_at=local(visit.starts_at), ends_at=local(visit.ends_at),
            duration_minutes=visit.duration_minutes, status=visit.status,
            started_at=local(visit.started_at), completed_at=local(visit.completed_at),
            canceled_at=local(visit.canceled_at), cancel_reason=visit.cancel_reason, memo=visit.memo,
            menus=[MenuBriefView(menu_id=m, name=menu_names[m]) for m in visit.menu_ids],
            status_changed_by_member_id=visit.status_changed_by_member_id,
        )
