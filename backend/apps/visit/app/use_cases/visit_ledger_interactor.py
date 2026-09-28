from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.upcoming_visit import UpcomingVisit
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.domain.services.visit_record_rules import cover_media_id
from visit.domain.services.visit_schedule import day_bounds, local_date


class VisitLedgerInteractor(VisitLedgerPort):
    """허브의 VisitLedgerPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(
        self, ledger: VisitLedgerRepository, records: VisitRecordRepository, reports: ReportRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._ledger = ledger
        self._records = records
        self._reports = reports
        self._now = now

    async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
        return await self._ledger.pet_has_visits(ctx, pet_id, active_only=False)

    async def pet_has_upcoming(self, ctx: ShopContext, pet_id: int) -> bool:
        return await self._ledger.pet_has_visits(ctx, pet_id, active_only=True)

    async def customer_has_upcoming(self, ctx: ShopContext, customer_id: int) -> bool:
        return await self._ledger.customer_has_active(ctx, customer_id)

    async def no_show_count(self, ctx: ShopContext, customer_id: int) -> int:
        return await self._ledger.count_no_show(ctx, customer_id)

    async def upcoming_for_customer(self, ctx: ShopContext, customer_id: int, limit: int) -> list[UpcomingVisit]:
        today_start, _ = day_bounds(local_date(self._now(), ctx.timezone), ctx.timezone)
        found = await self._ledger.list_active_from(ctx, customer_id, today_start, limit)
        return [UpcomingVisit(visit_id=v.id, pet_id=v.pet_id, starts_at=v.starts_at) for v in found]

    async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
        await self._ledger.clear_memos(ctx, customer_id)
        await self._records.clear_notes(ctx, customer_id)
        await self._reports.revoke_for_customer(ctx, customer_id, self._now())

    async def latest_covers(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
        latest = await self._records.latest_with_media(ctx, pet_ids)
        records = await self._records.list_many(ctx, list(latest.values()))
        return {pet_id: cover_media_id(records[visit_id].media) for pet_id, visit_id in latest.items()}
