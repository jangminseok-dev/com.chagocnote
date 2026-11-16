from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.services.pet_cards import PetCard


@dataclass(frozen=True)
class ListRevisitsQuery:
    ctx: ShopContext
    bucket: str            # soon · due
    cursor: str | None = None


@dataclass(frozen=True)
class RevisitItemView:
    pet: PetCard
    last_visit_date: date
    last_visit_id: int             # [예약]이 그 방문의 다음 예약 초안을 쓴다
    cycle_weeks: int               # 날짜에 쓴 주
    cycle_source: str              # manual · computed · single · none
    last_interval_weeks: int | None
    due_date: date
    estimated: bool                # 날짜가 어림인가(주기를 모른다)
    nudged_on: date | None         # 안내한 날 — 마지막 방문보다 뒤일 때만
    message: str                   # 템플릿에 값을 넣은 안내 글(보호자 이름·번호는 없다)


@dataclass(frozen=True)
class RevisitsView:
    items: list[RevisitItemView]
    next_cursor: str | None
