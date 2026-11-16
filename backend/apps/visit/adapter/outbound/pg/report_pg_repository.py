from __future__ import annotations

from datetime import datetime

from decimal import Decimal

from sqlalchemy import case, exists, extract, func, insert, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_visit
from visit.adapter.outbound.mappers.visit_report_mapper import to_report
from visit.adapter.outbound.orm.visit_orm import (
    VisitMenuOrm, VisitOrm, VisitRecordMediaOrm, VisitRecordOrm, VisitReportOrm,
)
from visit.app.dtos.guardian_report_dto import SentMedia, SentReport
from visit.app.dtos.report_target_dto import ReportTarget
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.domain.entities.visit_report import VisitReport
from visit.domain.services.guardian_cursor import MediaCursor


def _live(now: datetime) -> tuple:
    """VisitReport.is_live 와 같은 조건 — 끊지 않았고 기간이 지나지 않았다."""
    return (
        VisitReportOrm.revoked_at.is_(None),
        or_(VisitReportOrm.expires_at.is_(None), VisitReportOrm.expires_at > now),
    )


def _of_shop(ctx: ShopContext, *conditions):
    """이 매장의 방문에 달린 줄만 — visit_reports 에는 매장 칸이 없다."""
    return VisitReportOrm.visit_id.in_(select(VisitOrm.id).where(VisitOrm.shop_id == ctx.shop_id, *conditions))


class ReportPgRepository(ReportRepository, PublicReportRepository, GuardianReportRepository):
    """visit_reports 표 하나를 세 포트로 내놓는다 — 매장 범위(앱), 공개 조회(링크), 보호자용 읽기(로그인한 보호자)."""

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

    async def visit_ids_with_report(self, ctx: ShopContext, visit_ids: list[int]) -> set[int]:
        if not visit_ids:
            return set()
        rows = await self._session.execute(
            select(VisitReportOrm.visit_id).distinct().where(VisitReportOrm.visit_id.in_(visit_ids), _of_shop(ctx))
        )
        return set(rows.scalars())

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

    async def set_show_review(self, ctx: ShopContext, report_id: int, show_review: bool) -> None:
        await self._session.execute(
            update(VisitReportOrm).where(VisitReportOrm.id == report_id, _of_shop(ctx)).values(show_review=show_review))

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

    # --- 보호자용 읽기 -------------------------------------------------------------------------------------------

    @staticmethod
    def _sent_to(ctx: ShopContext, customer_id: int) -> tuple:
        """그 매장·그 고객의 방문에 달린, 끊지 않은 알림장(기간은 보지 않는다)과 기록이 있는 것."""
        return (
            VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
            VisitReportOrm.revoked_at.is_(None),
            exists().where(VisitRecordOrm.visit_id == VisitOrm.id),
        )

    async def list_sent(
        self, ctx: ShopContext, customer_id: int, *, pet_id: int | None, before: tuple[datetime, int] | None,
        limit: int,
    ) -> list[SentReport]:
        conditions = list(self._sent_to(ctx, customer_id))
        if pet_id is not None:
            conditions.append(VisitOrm.pet_id == pet_id)
        if before is not None:
            conditions.append(tuple_(VisitOrm.starts_at, VisitOrm.id) < before)
        rows = await self._session.execute(
            select(VisitReportOrm, VisitOrm)
            .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
            .where(*conditions)
            .order_by(VisitOrm.starts_at.desc(), VisitOrm.id.desc())
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [SentReport(report=to_report(report), visit=to_visit(visit, [])) for report, visit in rows]

    async def get_sent(self, ctx: ShopContext, customer_id: int, report_id: int) -> SentReport | None:
        found = (
            await self._session.execute(
                select(VisitReportOrm, VisitOrm)
                .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
                .where(VisitReportOrm.id == report_id, *self._sent_to(ctx, customer_id))
                .execution_options(populate_existing=True)
            )
        ).first()
        if found is None:
            return None
        report, visit = found
        menu_ids = await self._session.execute(
            select(VisitMenuOrm.menu_id).where(VisitMenuOrm.visit_id == visit.id).order_by(VisitMenuOrm.menu_id)
        )
        return SentReport(report=to_report(report), visit=to_visit(visit, list(menu_ids.scalars())))

    async def pet_ids_with_reports(self, ctx: ShopContext, customer_id: int) -> list[int]:
        rows = await self._session.execute(
            select(VisitOrm.pet_id)
            .join(VisitReportOrm, VisitReportOrm.visit_id == VisitOrm.id)
            .where(VisitOrm.pet_id.is_not(None), *self._sent_to(ctx, customer_id))
            .distinct()
            .order_by(VisitOrm.pet_id)
        )
        return list(rows.scalars())

    # --- 모아 보기(⑫) -------------------------------------------------------------------------------------------

    def _shown_media(self, ctx: ShopContext, customer_id: int, pet_id: int | None) -> list:
        """보호자가 볼 수 있는 알림장(`_sent_to`)의, 알림장에서 빼지 않은 미디어 — 한 장의 조립(`visible_media`)과 같다."""
        conditions = [*self._sent_to(ctx, customer_id), VisitRecordMediaOrm.hidden_from_report.is_(False)]
        if pet_id is not None:
            conditions.append(VisitOrm.pet_id == pet_id)
        return conditions

    @staticmethod
    def _year(ctx: ShopContext):
        return extract("year", func.timezone(ctx.timezone, VisitOrm.starts_at))

    async def list_media(
        self, ctx: ShopContext, customer_id: int, *, pet_id: int | None, year: int | None, phase: str | None,
        before: MediaCursor | None, limit: int,
    ) -> list[SentMedia]:
        M = VisitRecordMediaOrm
        conditions = self._shown_media(ctx, customer_id, pet_id)
        if year is not None:
            conditions.append(self._year(ctx) == year)
        if phase is not None:
            conditions.append(M.phase == phase)
        # 한 방문 안에서는 후 → 전, 순서대로 — 모두 내림차순으로 견주게 후를 1·전을 0 으로, 순서는 음수로 바꾼다.
        rank = case((M.phase == "after", 1), else_=0)
        if before is not None:
            starts_at, visit_id, phase_at, sort_order = before
            conditions.append(tuple_(VisitOrm.starts_at, VisitOrm.id, rank, -M.sort_order)
                              < tuple_(starts_at, visit_id, 1 if phase_at == "after" else 0, -sort_order))
        rows = await self._session.execute(
            select(VisitReportOrm.id, VisitOrm.id, VisitOrm.starts_at, M.media_id, M.kind, M.phase, M.sort_order)
            .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
            .join(M, M.visit_id == VisitOrm.id)
            .where(*conditions)
            .order_by(VisitOrm.starts_at.desc(), VisitOrm.id.desc(), rank.desc(), M.sort_order.asc())
            .limit(limit)
        )
        return [SentMedia(report_id=r, visit_id=v, starts_at=at, media_id=m, kind=k, phase=p, sort_order=o)
                for r, v, at, m, k, p, o in rows.all()]

    async def media_years(self, ctx: ShopContext, customer_id: int, *, pet_id: int | None) -> list[int]:
        year = self._year(ctx)
        rows = await self._session.execute(
            select(year)
            .select_from(VisitReportOrm)
            .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
            .join(VisitRecordMediaOrm, VisitRecordMediaOrm.visit_id == VisitOrm.id)
            .where(*self._shown_media(ctx, customer_id, pet_id))
            .group_by(year)
            .order_by(year.desc())
        )
        return [int(y) for y in rows.scalars()]

    async def weights(self, ctx: ShopContext, customer_id: int, pet_id: int, limit: int) -> list[tuple[datetime, Decimal]]:
        rows = await self._session.execute(
            select(VisitOrm.starts_at, VisitRecordOrm.weight_kg)
            .select_from(VisitReportOrm)
            .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
            .join(VisitRecordOrm, VisitRecordOrm.visit_id == VisitOrm.id)
            # 기록 표를 바로 잇는다 — `_sent_to` 의 "기록이 있다"(exists)와 같은 조건이다.
            .where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
                   VisitReportOrm.revoked_at.is_(None), VisitOrm.pet_id == pet_id,
                   VisitRecordOrm.weight_kg.is_not(None))
            .order_by(VisitOrm.starts_at.desc(), VisitOrm.id.desc())
            .limit(limit)
        )
        return [(at, kg) for at, kg in rows.all()]

