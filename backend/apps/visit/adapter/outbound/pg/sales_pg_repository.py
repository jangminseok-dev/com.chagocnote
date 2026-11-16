from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.sales_repository import SalesRepository, SalesVisitKind
from visit.domain.value_objects.sales import (
    DaySales,
    MenuSales,
    PetVisits,
    RemainingBookings,
    SalesTotals,
    SalesVisitRow,
)

DAY_PET_LIMIT = 5

# 방문이 든 날 — 시작 시각을 매장 시간대의 날짜로.
_DAY = "(v.starts_at AT TIME ZONE :tz)::date"
# 기간 조건. 경계는 매장 시간대의 자정을 시각으로 바꿔 넘긴다(색인 ix_visits_shop_starts_at 을 탄다).
_IN_RANGE = "v.shop_id = :shop AND v.starts_at >= :from_at AND v.starts_at < :to_at"

_LIST_KINDS = {
    "unrecorded": "v.status = 'completed' AND r.total_amount IS NULL",
    "no_show": "v.status = 'no_show'",
    "canceled": "v.status = 'canceled'",
    "menu": (
        "v.status = 'completed' AND r.total_amount IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM visit_record_items i WHERE i.visit_id = v.id AND i.menu_id = :menu_id)"
    ),
}


class SalesPgRepository(SalesRepository):
    """집계는 SQL 이 한다. 표가 여럿 얽히고 FILTER·DISTINCT ON 을 써서 ORM 식 대신 글로 쓴 질의를 둔다 —
    값은 전부 바인딩한다(글에 끼워 넣지 않는다)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _range(self, ctx: ShopContext, start: date, until: date) -> dict:
        zone = ZoneInfo(ctx.timezone)
        return {
            "shop": ctx.shop_id, "tz": ctx.timezone,
            "from_at": datetime.combine(start, time.min, zone),
            "to_at": datetime.combine(until, time.min, zone),
        }

    async def totals(self, ctx: ShopContext, start: date, until: date) -> SalesTotals:
        row = (await self._session.execute(text(f"""
            SELECT
              coalesce(sum(r.total_amount) FILTER (WHERE v.status = 'completed'), 0),
              count(*) FILTER (WHERE v.status = 'completed'),
              count(r.total_amount) FILTER (WHERE v.status = 'completed'),
              count(*) FILTER (WHERE v.status = 'completed' AND r.total_amount IS NULL),
              count(*) FILTER (WHERE v.status = 'no_show'),
              count(*) FILTER (WHERE v.status = 'canceled')
            FROM visits v LEFT JOIN visit_records r ON r.visit_id = v.id
            WHERE {_IN_RANGE}
        """), self._range(ctx, start, until))).one()
        return SalesTotals(*(int(value) for value in row))

    async def by_day(self, ctx: ShopContext, start: date, until: date) -> list[DaySales]:
        params = self._range(ctx, start, until)
        sums = (await self._session.execute(text(f"""
            SELECT {_DAY} AS day, coalesce(sum(r.total_amount), 0), count(*)
            FROM visits v LEFT JOIN visit_records r ON r.visit_id = v.id
            WHERE {_IN_RANGE} AND v.status = 'completed'
            GROUP BY day ORDER BY day
        """), params)).all()
        pets: dict[date, list[int]] = {}
        for day, pet_id in (await self._session.execute(text(f"""
            SELECT {_DAY} AS day, v.pet_id
            FROM visits v
            WHERE {_IN_RANGE} AND v.status = 'completed' AND v.pet_id IS NOT NULL
            GROUP BY day, v.pet_id ORDER BY day, min(v.starts_at), v.pet_id
        """), params)).all():
            seen = pets.setdefault(day, [])
            if len(seen) < DAY_PET_LIMIT:
                seen.append(pet_id)
        return [
            DaySales(day=day, revenue=int(revenue), completed=count, pet_ids=tuple(pets.get(day, ())))
            for day, revenue, count in sums
        ]

    async def by_payment(self, ctx: ShopContext, start: date, until: date) -> dict[str | None, int]:
        rows = (await self._session.execute(text(f"""
            SELECT r.payment_method, sum(r.total_amount)
            FROM visits v JOIN visit_records r ON r.visit_id = v.id
            WHERE {_IN_RANGE} AND v.status = 'completed' AND r.total_amount IS NOT NULL
            GROUP BY r.payment_method
        """), self._range(ctx, start, until))).all()
        return {method: int(amount) for method, amount in rows}

    async def by_menu(self, ctx: ShopContext, start: date, until: date) -> list[MenuSales]:
        params = self._range(ctx, start, until)
        priced = f"{_IN_RANGE} AND v.status = 'completed' AND r.total_amount IS NOT NULL"
        sums = (await self._session.execute(text(f"""
            SELECT i.menu_id, sum(i.amount) AS amount, count(*)
            FROM visits v JOIN visit_records r ON r.visit_id = v.id JOIN visit_record_items i ON i.visit_id = v.id
            WHERE {priced}
            GROUP BY i.menu_id ORDER BY amount DESC, i.menu_id
        """), params)).all()
        latest = dict((await self._session.execute(text(f"""
            SELECT DISTINCT ON (i.menu_id) i.menu_id, v.pet_id
            FROM visits v JOIN visit_records r ON r.visit_id = v.id JOIN visit_record_items i ON i.visit_id = v.id
            WHERE {priced} AND v.pet_id IS NOT NULL
            ORDER BY i.menu_id, v.starts_at DESC, v.id DESC
        """), params)).all())
        return [
            MenuSales(menu_id=menu_id, amount=int(amount), count=count, latest_pet_id=latest.get(menu_id))
            for menu_id, amount, count in sums
        ]

    async def pets(self, ctx: ShopContext, start: date, until: date) -> list[PetVisits]:
        rows = (await self._session.execute(text(f"""
            WITH seen AS (
              SELECT v.pet_id, count(*) AS visits, max({_DAY}) AS last_day
              FROM visits v
              WHERE {_IN_RANGE} AND v.status = 'completed' AND v.pet_id IS NOT NULL
              GROUP BY v.pet_id
            )
            SELECT seen.pet_id, seen.visits, seen.last_day, (
              SELECT min((f.starts_at AT TIME ZONE :tz)::date) FROM visits f
              WHERE f.shop_id = :shop AND f.pet_id = seen.pet_id AND f.status = 'completed'
            )
            FROM seen ORDER BY seen.last_day DESC, seen.pet_id
        """), self._range(ctx, start, until))).all()
        return [PetVisits(pet_id=p, visits=n, last_day=last, first_ever_day=first) for p, n, last, first in rows]

    async def remaining_reserved(self, ctx: ShopContext, since: datetime, until: date) -> RemainingBookings:
        params = {
            "shop": ctx.shop_id, "now": since,
            "to_at": datetime.combine(until, time.min, ZoneInfo(ctx.timezone)),
        }
        upcoming = "v.shop_id = :shop AND v.status = 'reserved' AND v.starts_at >= :now AND v.starts_at < :to_at"
        count = (await self._session.execute(text(f"SELECT count(*) FROM visits v WHERE {upcoming}"), params)).scalar_one()
        expected = (await self._session.execute(text(f"""
            SELECT sum(m.price)
            FROM visits v JOIN visit_menus vm ON vm.visit_id = v.id JOIN service_menus m ON m.id = vm.menu_id
            WHERE {upcoming} AND m.price IS NOT NULL
        """), params)).scalar_one()
        return RemainingBookings(count=count, expected_amount=None if expected is None else int(expected))

    async def report_counts(self, ctx: ShopContext, start: date, until: date) -> tuple[int, int]:
        sent, opened = (await self._session.execute(text(f"""
            SELECT count(DISTINCT v.id), count(DISTINCT v.id) FILTER (WHERE p.first_viewed_at IS NOT NULL)
            FROM visits v JOIN visit_reports p ON p.visit_id = v.id
            WHERE {_IN_RANGE} AND v.status = 'completed'
        """), self._range(ctx, start, until))).one()
        return sent, opened

    async def list_visits(
        self, ctx: ShopContext, start: date, until: date, kind: SalesVisitKind, menu_id: int | None,
        before: tuple[datetime, int] | None, limit: int,
    ) -> list[SalesVisitRow]:
        params = {**self._range(ctx, start, until), "limit": limit}
        where = f"{_IN_RANGE} AND {_LIST_KINDS[kind]}"
        if kind == "menu":
            params["menu_id"] = menu_id
        if before is not None:
            where += " AND (v.starts_at, v.id) < (:before_at, :before_id)"
            params["before_at"], params["before_id"] = before
        rows = (await self._session.execute(text(f"""
            SELECT v.id, v.starts_at, {_DAY}, v.pet_id, v.customer_id, r.total_amount
            FROM visits v LEFT JOIN visit_records r ON r.visit_id = v.id
            WHERE {where}
            ORDER BY v.starts_at DESC, v.id DESC LIMIT :limit
        """), params)).all()
        return [SalesVisitRow(*row) for row in rows]
