from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.services.pet_cards import PetCard


@dataclass(frozen=True)
class ListDuePetsQuery:
    ctx: ShopContext
    cursor: str | None


@dataclass(frozen=True)
class DuePetItemView:
    pet: PetCard
    last_visit_date: date


@dataclass(frozen=True)
class DuePetsView:
    items: list[DuePetItemView]
    next_cursor: str | None
