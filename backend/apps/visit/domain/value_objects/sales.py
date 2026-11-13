"""매출 집계가 돌려주는 값들(설계 ⑧ 3.1). 날짜는 모두 매장 시간대의 날짜다."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SalesTotals:
    """기간의 합계. revenue 는 완료 방문의 총액 합, priced 는 총액을 적은 완료 방문 수,
    unrecorded 는 총액이 없는(기록이 없는 것도) 완료 방문 수다. completed = priced + unrecorded."""

    revenue: int
    completed: int
    priced: int
    unrecorded: int
    no_show: int
    canceled: int


@dataclass(frozen=True)
class DaySales:
    """완료 방문이 있는 하루. pet_ids 는 그날 온 아이(시작 순, 겹치지 않게, 다섯까지)."""

    day: date
    revenue: int
    completed: int
    pet_ids: tuple[int, ...]


@dataclass(frozen=True)
class MenuSales:
    """메뉴 하나의 항목 금액 합과 건수. latest_pet_id 는 그 메뉴를 가장 최근에 한 아이(없으면 None)."""

    menu_id: int
    amount: int
    count: int
    latest_pet_id: int | None


@dataclass(frozen=True)
class PetVisits:
    """기간에 온 아이 하나 — 기간 안의 완료 방문 수와 마지막 날, 이 매장에서의 첫 완료 방문일."""

    pet_id: int
    visits: int
    last_day: date
    first_ever_day: date


@dataclass(frozen=True)
class RemainingBookings:
    """남은 예약의 수와 그 예약들이 고른 메뉴의 정가 합. 정가가 있는 메뉴가 하나도 없으면 None."""

    count: int
    expected_amount: int | None


@dataclass(frozen=True)
class SalesVisitRow:
    """매출 탭에서 이어지는 방문 목록의 한 줄."""

    visit_id: int
    starts_at: datetime
    day: date
    pet_id: int | None
    customer_id: int
    amount: int | None


@dataclass(frozen=True)
class DuePet:
    """다시 올 때가 지난 아이 후보 — 마지막 완료 방문일."""

    pet_id: int
    last_day: date
