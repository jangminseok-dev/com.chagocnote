from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_visit
from visit.adapter.outbound.mappers.visit_report_mapper import to_report
from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm, VisitReportOrm
from visit.app.dtos.report_target_dto import ReportTarget
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.domain.entities.visit_report import VisitReport


def _live(now: datetime) -> tuple:
    """VisitReport.is_live 와 같은 조건 — 끊지 않았고 기간이 지나지 않았다."""
    return (
        VisitReportOrm.revoked_at.is_(None),
        or_(VisitReportOrm.expires_at.is_(None), VisitReportOrm.expires_at > now),
    )


def _of_shop(ctx: ShopContext, *conditions):
    """이 매장의 방문에 달린 줄만 — visit_reports 에는 매장 칸이 없다."""
    return VisitReportOrm.visit_id.in_(select(VisitOrm.id).where(VisitOrm.shop_id == ctx.shop_id, *conditions))


class ReportPgRepository(ReportRepository, PublicReportRepository):
    """visit_reports 표 하나를 두 포트로 내놓는다 — 매장 범위(앱)와 공개 조회(보호자 웹)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_live(self, ctx: ShopContext, visit_id: int, now: datetime) -> VisitReport | None:
        row = (
            await self._session.execute(
                select(VisitReportOrm)
                .where(VisitReportOrm.visit_id == visit_id, _of_shop(ctx), *_live(now))
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_report(row) if row is not None else None

    async def live_visit_ids(self, ctx: ShopContext, visit_ids: list[int], now: datetime) -> set[int]:
        if not visit_ids:
            return set()
        rows = await self._session.execute(
            select(VisitReportOrm.visit_id)
            .where(VisitReportOrm.visit_id.in_(visit_ids), _of_shop(ctx), *_live(now))
        )
        return set(rows.scalars())

    async def close_expired(self, ctx: ShopContext, visit_id: int, now: datetime) -> None:
        await self._session.execute(
            update(VisitReportOrm)
            .where(VisitReportOrm.visit_id == visit_id, _of_shop(ctx), VisitReportOrm.revoked_at.is_(None),
                   VisitReportOrm.expires_at <= now)
            .values(revoked_at=now)
        )

    async def create(
        self, ctx: ShopContext, visit_id: int, public_id: bytes, expires_at: datetime | None, now: datetime
    ) -> VisitReport:
        row = (
            await self._session.execute(
                insert(VisitReportOrm)
                .values(visit_id=visit_id, public_id=public_id, expires_at=expires_at,
                        created_by_member_id=ctx.member_id, created_at=now)
                .returning(VisitReportOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_report(row)

    async def revoke(self, ctx: ShopContext, visit_id: int, now: datetime) -> bool:
        revoked = await self._session.execute(
            update(VisitReportOrm)
            .where(VisitReportOrm.visit_id == visit_id, _of_shop(ctx), *_live(now))
            .values(revoked_at=now)
            .returning(VisitReportOrm.id)
        )
        return revoked.first() is not None

    async def revoke_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        await self._session.execute(
            update(VisitReportOrm)
            .where(_of_shop(ctx, VisitOrm.customer_id == customer_id), VisitReportOrm.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def find(self, public_id: bytes) -> ReportTarget | None:
        found = (
            await self._session.execute(
                select(VisitReportOrm, VisitOrm)
                .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
                .where(VisitReportOrm.public_id == public_id)
                .execution_options(populate_existing=True)
            )
        ).first()
        if found is None:
            return None
        report, visit = found
        menu_ids = await self._session.execute(
            select(VisitMenuOrm.menu_id).where(VisitMenuOrm.visit_id == visit.id).order_by(VisitMenuOrm.menu_id)
        )
        return ReportTarget(
            report=to_report(report), shop_id=visit.shop_id, visit=to_visit(visit, list(menu_ids.scalars()))
        )

    async def mark_viewed(self, report_id: int, now: datetime) -> None:
        await self._session.execute(
            update(VisitReportOrm)
            .where(VisitReportOrm.id == report_id, VisitReportOrm.first_viewed_at.is_(None))
            .values(first_viewed_at=now)
        )
