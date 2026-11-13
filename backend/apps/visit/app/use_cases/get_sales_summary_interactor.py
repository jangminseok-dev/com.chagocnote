from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.get_sales_summary_dto import (
    BookingsView,
    BucketView,
    CompareView,
    CompareWindowView,
    GetSalesSummaryQuery,
    GoalView,
    MenuView,
    PaymentView,
    PeriodView,
    PetsView,
    RegularView,
    ReportView,
    SalesSummaryView,
)
from visit.app.ports.input.get_sales_summary_use_case import GetSalesSummaryUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.sales_goal_repository import SalesGoalRepository
from visit.app.ports.output.sales_repository import SalesRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.due_pets import due_pets, start_of_day
from visit.app.services.pet_cards import pet_cards, showable_pets
from visit.domain.services.sales_period import (
    Period,
    bucket_keys,
    check_anchor,
    compare_window,
    elapsed_end,
    period_of,
    previous_of,
    year_ago_of,
)
from visit.domain.value_objects.sales import DaySales, PetVisits

FACE_LIMIT, NEW_LIMIT, RETURNING_LIMIT, REGULAR_LIMIT = 6, 3, 4, 3
PAYMENT_ORDER = ("card", "cash", "transfer", None)
ADJUSTMENT_NAME = "조정"
_DAY = timedelta(days=1)


class GetSalesSummaryInteractor(GetSalesSummaryUseCase):
    """매출 탭 한 화면(설계 ⑧ 3.2). 낱말의 뜻(3.1)을 여기서 맞춘다 — 저장소는 세기만 한다.

    질의 수는 방문·아이 수와 상관없다.
    """

    def __init__(
        self, sales: SalesRepository, goals: SalesGoalRepository, menus: MenuRepository,
        directory: CustomerDirectoryPort, records: VisitRecordRepository, library: MediaLibraryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._sales = sales
        self._goals = goals
        self._menus = menus
        self._directory = directory
        self._records = records
        self._library = library
        self._now = now

    async def get_sales_summary(self, query: GetSalesSummaryQuery) -> SalesSummaryView:
        ctx = query.ctx
        now = self._now()
        today = now.astimezone(ZoneInfo(ctx.timezone)).date()
        period = period_of(query.span, check_anchor(query.anchor) if query.anchor else today)
        current = period.contains(today)

        totals = await self._sales.totals(ctx, period.start, period.until)
        days = await self._sales.by_day(ctx, period.start, period.until)
        payments = await self._sales.by_payment(ctx, period.start, period.until)
        menu_sales = await self._sales.by_menu(ctx, period.start, period.until)
        seen = await self._sales.pets(ctx, period.start, period.until)
        regular_rows = await self._regulars(ctx, period, seen, today)
        due, _ = await due_pets(ctx, self._sales, self._directory, today)
        remaining = await self._sales.remaining_reserved(ctx, start_of_day(ctx, today), period.until) \
            if current else None
        report = await self._sales.report_counts(ctx, period.start, period.until) if totals.completed else None
        goal = await self._goals.get(ctx) if query.span == "month" and current else None

        # 아이 — 이름을 보일 수 있는 아이를 한 번에 가리고, 화면에 나올 아이의 사진만 읽는다.
        pets = await showable_pets(
            ctx,
            [p.pet_id for p in seen] + [p.pet_id for p in regular_rows]
            + [m.latest_pet_id for m in menu_sales if m.latest_pet_id is not None]
            + [pet_id for day in days for pet_id in day.pet_ids],
            self._directory,
        )
        first_time = [p for p in seen if period.contains(p.first_ever_day)]
        returning = [p for p in seen if not period.contains(p.first_ever_day)]

        def pick(rows: list[PetVisits], limit: int) -> list[int]:
            return [p.pet_id for p in rows if p.pet_id in pets][:limit]

        face_ids, new_ids = pick(seen, FACE_LIMIT), pick(first_time, NEW_LIMIT)
        returning_ids, regular_ids = pick(returning, RETURNING_LIMIT), pick(regular_rows, REGULAR_LIMIT)
        day_pets = {day.day: [p for p in day.pet_ids if p in pets] for day in days} if query.span != "year" else {}
        cards = await pet_cards(
            ctx, pets,
            face_ids + new_ids + returning_ids + regular_ids
            + [m.latest_pet_id for m in menu_sales if m.latest_pet_id is not None]
            + [pet_id for ids in day_pets.values() for pet_id in ids],
            self._records, self._library,
        )
        regular_visits = {p.pet_id: p.visits for p in regular_rows}

        item_total = sum(m.amount for m in menu_sales)
        names = {m.id: m.name for m in await self._menus.list_by_ids(ctx, [m.menu_id for m in menu_sales])} \
            if menu_sales else {}
        menus = [
            MenuView(menu_id=m.menu_id, name=names.get(m.menu_id, ""), amount=m.amount, count=m.count,
                     pet=cards.get(m.latest_pet_id))
            for m in menu_sales
        ]
        if totals.revenue != item_total:
            # 총액은 항목 합과 별개다(할인·추가금). 차이를 한 줄로 보여 합이 맞게 한다.
            menus.append(MenuView(menu_id=None, name=ADJUSTMENT_NAME, amount=totals.revenue - item_total,
                                  count=0, pet=None))

        return SalesSummaryView(
            span=query.span,
            period=PeriodView(start=period.start, end=period.end, elapsed_end=elapsed_end(period, today)),
            revenue=totals.revenue,
            visit_count=totals.completed,
            priced_count=totals.priced,
            average=totals.revenue // totals.priced if totals.priced else None,
            compare=await self._compare(ctx, period, today),
            goal=GoalView(monthly_amount=goal) if goal is not None else None,
            pets=PetsView(
                count=len(seen), new_count=len(first_time), returning_count=len(returning),
                faces=[cards[i] for i in face_ids], new=[cards[i] for i in new_ids],
                returning=[cards[i] for i in returning_ids],
            ),
            buckets=_buckets(period, days, today, {day: [cards[i] for i in ids] for day, ids in day_pets.items()}),
            payments=[
                PaymentView(method=method or "none", amount=payments[method])
                for method in PAYMENT_ORDER if payments.get(method)
            ],
            menus=menus,
            regulars=[RegularView(pet=cards[i], visit_count=regular_visits[i]) for i in regular_ids],
            bookings=BookingsView(
                remaining=remaining.count if remaining else None,
                expected_amount=remaining.expected_amount if remaining else None,
                no_show=totals.no_show, canceled=totals.canceled,
            ),
            weekdays=_weekdays(days) if query.span in ("month", "year") else None,
            report=ReportView(completed=totals.completed, sent=report[0], opened=report[1]) if report else None,
            unrecorded_count=totals.unrecorded,
            due_pet_count=len(due),
        )

    async def _compare(self, ctx, period: Period, today: date) -> CompareView:
        async def window(other: Period | None) -> CompareWindowView | None:
            found = compare_window(period, other, today) if other is not None else None
            if found is None:
                return None
            start, end = found
            return CompareWindowView(
                start=start, end=end, revenue=(await self._sales.totals(ctx, start, end + _DAY)).revenue)

        year_ago = await window(year_ago_of(period))
        return CompareView(
            previous=await window(previous_of(period)),
            # 작년에 매출이 없었으면(막 시작한 매장) 견줄 것이 없다.
            year_ago=year_ago if year_ago is not None and year_ago.revenue > 0 else None,
        )

    async def _regulars(self, ctx, period: Period, seen: list[PetVisits], today: date) -> list[PetVisits]:
        """단골 — 보고 있는 기간이 든 해(오늘까지)에 가장 자주 온 아이. 같으면 최근에 온 아이가 앞이다."""
        reached = elapsed_end(period, today)
        if reached is None:
            return []
        rows = seen if period.span == "year" else await self._sales.pets(
            ctx, date(reached.year, 1, 1), min(date(reached.year, 12, 31), today) + _DAY)
        return sorted(rows, key=lambda p: (-p.visits, -p.last_day.toordinal(), p.pet_id))


def _buckets(period: Period, days: list[DaySales], today: date, pets: dict[date, list]) -> list[BucketView]:
    by_day = {day.day: day for day in days}
    if period.span == "year":
        months: dict[int, list[DaySales]] = {}
        for day in days:
            months.setdefault(day.day.month, []).append(day)
        return [
            BucketView(
                key=f"{key.year:04d}-{key.month:02d}",
                revenue=sum(d.revenue for d in months.get(key.month, [])),
                visit_count=sum(d.completed for d in months.get(key.month, [])),
                future=key > today, pets=[],
            )
            for key in bucket_keys(period)
        ]
    return [
        BucketView(
            key=key.isoformat(),
            revenue=by_day[key].revenue if key in by_day else 0,
            visit_count=by_day[key].completed if key in by_day else 0,
            future=key > today, pets=pets.get(key, []),
        )
        for key in bucket_keys(period)
    ]


def _weekdays(days: list[DaySales]) -> list[int]:
    """요일별 매출 — 월요일부터 일요일까지."""
    sums = [0] * 7
    for day in days:
        sums[day.day.weekday()] += day.revenue
    return sums
