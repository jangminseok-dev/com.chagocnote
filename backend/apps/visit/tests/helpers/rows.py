"""통합 테스트가 방문 행을 상태째 바로 넣는 도우미 — 상태에 맞는 시각·사유 칸을 채운다(CHECK 제약)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from visit.adapter.outbound.orm.visit_orm import VisitOrm


async def insert_visit(
    session: AsyncSession, starts_at: datetime, status: str = "reserved", shop_id: int = 1,
    customer_id: int = 1, pet_id: int | None = 101, duration_minutes: int = 90, memo: str | None = None,
) -> int:
    started = starts_at if status in ("in_progress", "completed") else None
    return (
        await session.execute(
            insert(VisitOrm)
            .values(
                shop_id=shop_id, customer_id=customer_id, pet_id=pet_id, starts_at=starts_at,
                duration_minutes=duration_minutes, status=status, started_at=started,
                completed_at=starts_at if status == "completed" else None,
                canceled_at=starts_at if status == "canceled" else None,
                cancel_reason="customer_request" if status == "canceled" else None,
                memo=memo, created_by_member_id=11,
            )
            .returning(VisitOrm.id)
        )
    ).scalar_one()
