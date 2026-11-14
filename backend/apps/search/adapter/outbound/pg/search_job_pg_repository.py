from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from search.adapter.outbound.orm.search_orm import SearchJobOrm as _J
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.domain.entities.search_document import ReindexJob
from search.domain.services.retry import CLAIM_HOLD, retry_delay


class SearchJobPgRepository(ReindexQueueRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, ctx: ShopContext, scope: str, ref_id: int, now: datetime) -> None:
        await self._session.execute(
            insert(_J)
            .values(shop_id=ctx.shop_id, scope=scope, ref_id=ref_id, enqueued_at=now, next_attempt_at=now)
            .on_conflict_do_update(
                constraint="uq_search_jobs_target",
                set_=dict(generation=_J.generation + 1, attempts=0, enqueued_at=now, next_attempt_at=now),
            )
        )

    # --- 전 매장(색인기) -----------------------------------------------------------------------------------------

    async def claim_due(self, now: datetime, limit: int) -> list[ReindexJob]:
        due = (
            select(_J.id)
            .where(_J.next_attempt_at <= now)
            .order_by(_J.next_attempt_at, _J.id)
            .limit(limit)
            .with_for_update(skip_locked=True)   # 다른 색인기가 쥔 줄은 건너뛴다
        )
        rows = await self._session.execute(
            update(_J).where(_J.id.in_(due)).values(next_attempt_at=now + CLAIM_HOLD)
            .returning(_J.id, _J.shop_id, _J.scope, _J.ref_id, _J.generation, _J.attempts, _J.enqueued_at)
        )
        claimed = sorted(rows, key=lambda r: (r.enqueued_at, r.id))
        return [
            ReindexJob(id=r.id, shop_id=r.shop_id, scope=r.scope, ref_id=r.ref_id, generation=r.generation,
                       attempts=r.attempts)
            for r in claimed
        ]

    async def finish(self, job: ReindexJob) -> None:
        await self._session.execute(delete(_J).where(_J.id == job.id, _J.generation == job.generation))

    async def retry_later(self, job: ReindexJob, now: datetime) -> None:
        await self._session.execute(
            update(_J)
            .where(_J.id == job.id, _J.generation == job.generation)
            .values(attempts=_J.attempts + 1, next_attempt_at=now + retry_delay(job.attempts))
        )
