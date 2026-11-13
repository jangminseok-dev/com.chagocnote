from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.services.pet_cards import PetCard
from visit.domain.services.sales_period import Span


@dataclass(frozen=True)
class GetSalesSummaryQuery:
    ctx: ShopContext
    span: Span
    anchor: date | None   # 그 기간 안의 아무 날. 없으면 매장 시간대의 오늘


@dataclass(frozen=True)
class PeriodView:
    start: date
    end: date
    elapsed_end: date | None   # 지나간 마지막 날. 아직 오지 않은 기간이면 None


@dataclass(frozen=True)
class CompareWindowView:
    """견준 창과 그 창의 매출."""

    start: date
    end: date
    revenue: int


@dataclass(frozen=True)
class CompareView:
    previous: CompareWindowView | None   # 바로 앞 기간(진행 중이면 같은 길이만큼)
    year_ago: CompareWindowView | None   # 작년 같은 때 — 매출이 있었을 때만


@dataclass(frozen=True)
class GoalView:
    monthly_amount: int


@dataclass(frozen=True)
class PetsView:
    count: int               # 기간에 온 아이 수(이름을 보일 수 없는 아이도 센다)
    new_count: int           # 이 기간에 처음 온 아이
    returning_count: int
    faces: list[PetCard]     # 최근에 온 순 여섯
    new: list[PetCard]       # 셋까지
    returning: list[PetCard]  # 넷까지


@dataclass(frozen=True)
class BucketView:
    key: str                 # 날이면 YYYY-MM-DD, 달이면 YYYY-MM
    revenue: int
    visit_count: int
    future: bool             # 오늘 뒤
    pets: list[PetCard]      # 그날의 아이들(다섯까지). 달 칸에는 없다


@dataclass(frozen=True)
class PaymentView:
    method: str              # card · cash · transfer · none(고르지 않음)
    amount: int


@dataclass(frozen=True)
class MenuView:
    menu_id: int | None      # 조정 줄이면 None
    name: str
    amount: int
    count: int
    pet: PetCard | None      # 그 메뉴를 가장 최근에 한 아이


@dataclass(frozen=True)
class RegularView:
    pet: PetCard
    visit_count: int


@dataclass(frozen=True)
class BookingsView:
    remaining: int | None         # 지금부터 기간 끝까지의 예약. 진행 중인 기간에만
    expected_amount: int | None   # 그 예약들의 정가 합. 정가가 없으면 None
    no_show: int
    canceled: int


@dataclass(frozen=True)
class ReportView:
    completed: int
    sent: int
    opened: int


@dataclass(frozen=True)
class SalesSummaryView:
    span: Span
    period: PeriodView
    revenue: int
    visit_count: int
    priced_count: int
    average: int | None
    compare: CompareView
    goal: GoalView | None
    pets: PetsView
    buckets: list[BucketView]
    payments: list[PaymentView]
    menus: list[MenuView]
    regulars: list[RegularView]
    bookings: BookingsView
    weekdays: list[int] | None   # 월~일 매출. 월·연 보기에만
    report: ReportView | None    # 완료 방문이 없으면 None
    unrecorded_count: int
    due_pet_count: int
