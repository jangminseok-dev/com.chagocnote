"""색인기 조립과 루프 — 기동 때 asyncio 작업 하나가 돈다(⑨ 설계 3.4). 테스트는 루프 대신 build_indexer(...).run_once()."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import session_scope
from search.app.ports.output.embedding_port import EmbeddingPort
from search.app.services.indexer import DEFAULT_BATCH, Indexer, IndexReport
from search.app.services.indexer_wakeup import wait
from search.dependencies.indexer_ports import indexer_ports
from search.dependencies.search_wiring import build_document_repository, build_queue_repository, get_embedder
from search.domain.services.clock import utc_now

logger = logging.getLogger("search.indexer")

WAKE_SETTLE_SECONDS = 0.5      # 깨운 쪽(구독자)의 커밋이 먼저 닿게
INTERVAL_SECONDS = 2.0


def build_indexer(
    db: AsyncSession, *, embedder: EmbeddingPort | None = None, now: Callable[[], datetime] | None = None
) -> Indexer:
    ports = indexer_ports()
    customer_source = ports.customer_source(db)
    return Indexer(
        queue=build_queue_repository(db), documents=build_document_repository(db),
        embedder=embedder if embedder is not None else get_embedder(),
        sources={"visit": ports.visit_source(db), "pet": customer_source, "customer": customer_source},
        shops=ports.shop_profile(db), directory=ports.customer_directory(db),
        commit=db.commit, rollback=db.rollback, now=now if now is not None else utc_now,
    )


async def run_once() -> IndexReport:
    async with session_scope() as db:
        return await build_indexer(db).run_once()


async def run_forever(stop: asyncio.Event, interval: float = INTERVAL_SECONDS) -> None:
    """stop 까지: interval 초마다 또는 깨우면 돈다 — 줄이 남아 있는 동안은 이어서. 한 번의 예외는 로그 뒤 다음 번으로."""
    while not stop.is_set():
        await wait(interval)
        if stop.is_set():
            return
        await asyncio.sleep(WAKE_SETTLE_SECONDS)
        if stop.is_set():
            return
        try:
            # 줄이 가득 집혔으면 더 있다 — 기다리지 않고 이어 돈다(처음 채울 때).
            while not stop.is_set() and (await run_once()).claimed >= DEFAULT_BATCH:
                pass
        except Exception as exc:
            logger.warning("색인기 루프 한 번이 실패했습니다 (%s). 다음 번에 다시 돕니다.", type(exc).__name__)


def start_indexer() -> tuple[asyncio.Task, asyncio.Event]:
    """main.py 의 lifespan 이 부른다. 끝낼 때 stop.set() 과 wake() 뒤 task 를 기다린다."""
    stop = asyncio.Event()
    task = asyncio.create_task(run_forever(stop), name="search-indexer")
    return task, stop
