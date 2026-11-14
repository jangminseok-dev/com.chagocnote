from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import VisitOrm
from visit.app.ports.output.visit_check_repository import HistoryAsk, NoShowAsk, VisitCheckRepository
from visit.domain.entities.visit import COMPLETED, NO_SHOW


class VisitCheckPgRepository(VisitCheckRepository):
    """물음들을 덮는 범위를 한 번에 읽고 물음마다 나눈다 — 방문 수와 상관없이 질의가 하나다.

    읽는 줄은 그날 예약한 아이들의 완료 방문(아이마다 수십 줄)과 보호자들의 지난 1년 노쇼라 많지 않다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def last_completed(self, ctx: ShopContext, asks: list[HistoryAsk]) -> dict[int, datetime | None]:
        if not asks:
            return {}
        rows = (
            await self._session.execute(
                select(VisitOrm.pet_id, VisitOrm.starts_at).where(
                    VisitOrm.shop_id == ctx.shop_id,
                    VisitOrm.pet_id.in_({ask.pet_id for ask in asks}),
                    VisitOrm.status == COMPLETED,
                    VisitOrm.starts_at < max(ask.before for ask in asks),
                )
            )
        ).all()
        starts: dict[int, list[datetime]] = {}
        for pet_id, starts_at in rows:
            starts.setdefault(pet_id, []).append(starts_at)
        return {
            ask.key: max((s for s in starts.get(ask.pet_id, ()) if s < ask.before), default=None)
            for ask in asks
        }

    async def no_shows(self, ctx: ShopContext, asks: list[NoShowAsk]) -> dict[int, int]:
        if not asks:
            return {}
        rows = (
            await self._session.execute(
                select(VisitOrm.customer_id, VisitOrm.starts_at).where(
                    VisitOrm.shop_id == ctx.shop_id,
                    VisitOrm.customer_id.in_({ask.customer_id for ask in asks}),
                    VisitOrm.status == NO_SHOW,
                    VisitOrm.starts_at >= min(ask.since for ask in asks),
                    VisitOrm.starts_at < max(ask.until for ask in asks),
                )
            )
        ).all()
        starts: dict[int, list[datetime]] = {}
        for customer_id, starts_at in rows:
            starts.setdefault(customer_id, []).append(starts_at)
        return {
            ask.key: sum(1 for s in starts.get(ask.customer_id, ()) if ask.since <= s < ask.until)
            for ask in asks
        }
