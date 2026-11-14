"""Observer — core/observer 버스에 등록되는 구독자. main.py 가 import 때 subscribe 로 꽂는다(⑨ 설계 3.4).

발행한 visit·customer 인터랙터와 같은 세션·같은 트랜잭션에서 돈다 — 쓰기가 롤백되면 줄도 사라진다.
줄 하나만 쓴다. 원본을 읽지도 임베딩 프로세스를 부르지도 않는다.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.search_events import SearchSourceChanged
from search.adapter.outbound.pg.search_job_pg_repository import SearchJobPgRepository
from search.app.dtos.enqueue_reindex_dto import EnqueueReindexCommand
from search.app.services.indexer_wakeup import wake
from search.app.use_cases.enqueue_reindex_interactor import EnqueueReindexInteractor
from search.domain.services.clock import utc_now


async def handle_source_changed(session: AsyncSession, event: SearchSourceChanged) -> None:
    use_case = EnqueueReindexInteractor(queue=SearchJobPgRepository(session), now=utc_now)
    await use_case.enqueue_reindex(EnqueueReindexCommand(ctx=event.ctx, scope=event.scope, ref_id=event.ref_id))
    wake()   # 루프가 반 초 뒤(요청의 커밋 뒤) 돈다
