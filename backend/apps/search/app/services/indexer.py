"""색인기 — 다시 색인할 줄을 집어 검색 문서를 원본에 맞춘다(⑨ 설계 3.4). 요청 밖에서 돈다.

한 줄의 차례: 집고 커밋(잠금을 놓는다) → 원본과 저장된 문서를 읽고 커밋 → 바뀐 글만 임베딩(트랜잭션도 잠금도 없이)
→ 고객 행을 잠그고 원본을 다시 읽어 같을 때만 갈아 끼운다 → 줄을 지우거나 미룬다 → 커밋.
로그에는 shop_id·scope·ref_id·예외의 형 이름만 — 글·벡터·예외 문자열은 찍지 않는다.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.search_source import SourceDocument
from hub.app.dtos.shop_context import system_context
from hub.app.errors import FamilyNotFoundError
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.search_source_port import SearchSourcePort
from hub.app.ports.shop_profile_port import ShopProfilePort
from search.app.ports.output.embedding_port import INDEX_TIMEOUT, EmbeddingPort
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.app.ports.output.search_document_repository import SearchDocumentRepository
from search.domain.entities.search_document import ReindexJob, SearchDocument
from search.domain.services.embedding_model import CURRENT_MODEL

logger = logging.getLogger("search.indexer")

DEFAULT_BATCH = 20


@dataclass(frozen=True)
class IndexReport:
    claimed: int = 0
    indexed: int = 0     # 문서를 맞추고 줄을 끝냈다
    deferred: int = 0    # 줄을 남겼다 — 임베딩을 못 받았거나, 그 사이 원본이 바뀌었거나, 던졌다


class Indexer:
    def __init__(
        self, *, queue: ReindexQueueRepository, documents: SearchDocumentRepository, embedder: EmbeddingPort,
        sources: Mapping[str, SearchSourcePort], shops: ShopProfilePort, directory: CustomerDirectoryPort,
        commit: Callable[[], Awaitable[None]], rollback: Callable[[], Awaitable[None]],
        now: Callable[[], datetime], batch: int = DEFAULT_BATCH,
    ) -> None:
        self._queue = queue
        self._documents = documents
        self._embedder = embedder
        self._sources = sources
        self._shops = shops
        self._directory = directory
        self._commit = commit
        self._rollback = rollback
        self._now = now
        self._batch = batch

    async def run_once(self) -> IndexReport:
        jobs = await self._queue.claim_due(self._now(), self._batch)
        await self._commit()   # 집은 줄의 잠금을 놓는다 — 줄은 CLAIM_HOLD 만큼 뒤로 밀려 있다
        indexed = 0
        for job in jobs:
            try:
                indexed += await self._index(job)
            except Exception as exc:
                # 한 줄의 실패가 세션을 깨뜨려 같은 묶음의 뒤 줄을 막지 않게 되돌리고 그 줄만 미룬다.
                await self._rollback()
                logger.warning("색인에 실패했습니다 (shop_id=%d, %s %d, %s). 뒤에 다시 합니다.",
                               job.shop_id, job.scope, job.ref_id, type(exc).__name__)
                await self._defer(job)
        return IndexReport(claimed=len(jobs), indexed=indexed, deferred=len(jobs) - indexed)

    async def _defer(self, job: ReindexJob) -> None:
        try:
            await self._queue.retry_later(job, self._now())
            await self._commit()
        except Exception as exc:   # 미루지 못해도 줄은 남아 있다(CLAIM_HOLD 뒤에 다시 집힌다)
            await self._rollback()
            logger.warning("줄을 미루지 못했습니다 (shop_id=%d, %s %d, %s).",
                           job.shop_id, job.scope, job.ref_id, type(exc).__name__)

    async def _index(self, job: ReindexJob) -> bool:
        """문서를 맞추고 줄을 끝냈으면 True, 줄을 남겼으면 False."""
        profile = await self._shops.public_profile(job.shop_id)
        ctx = system_context(job.shop_id, profile.timezone if profile is not None else "Asia/Seoul")
        source = self._sources.get(job.scope)
        wanted = await source.documents(ctx, job.scope, job.ref_id) if profile is not None and source else []
        if not wanted:   # 글을 비웠거나, 지웠거나, 익명화했거나, 매장이 없다
            return await self._settle(job, ctx, [], finished=True)

        stored = {(d.kind, d.source_id): d for d in await self._documents.list_for_target(ctx, job.scope, job.ref_id)}
        await self._commit()   # 읽기를 닫는다 — 임베딩을 부르는 동안 트랜잭션을 열어 두지 않는다

        def reusable(d: SourceDocument) -> SearchDocument | None:
            kept = stored.get((d.kind, d.source_id))
            same = kept is not None and kept.body == d.body and kept.embedding is not None
            return kept if same and kept.model == CURRENT_MODEL else None

        fresh = [d for d in wanted if reusable(d) is None]
        embedded = await self._embedder.embed("passage", [d.body for d in fresh], INDEX_TIMEOUT) if fresh else None
        vectors = dict(zip(((d.kind, d.source_id) for d in fresh), embedded.vectors)) if embedded is not None else {}

        # 여기서부터 쓰는 트랜잭션 — 고객 행 → 검색 표. 익명화·수정과 겹치지 않게 고객 행부터 잠근다.
        try:
            await self._directory.lock_family(ctx, wanted[0].customer_id, ())
        except FamilyNotFoundError:   # 임베딩하는 사이에 익명화됐다 — 옛 글을 되살리지 않는다
            return await self._settle(job, ctx, [], finished=True)
        if await source.documents(ctx, job.scope, job.ref_id) != wanted:
            await self._rollback()    # 그 사이에 바뀌었다 — 쓰지 않는다. 줄은 남아 있어 뒤에 다시 집힌다
            return False

        documents = []
        for d in wanted:
            kept, vector = reusable(d), vectors.get((d.kind, d.source_id))
            documents.append(SearchDocument(
                kind=d.kind, source_id=d.source_id, customer_id=d.customer_id, pet_id=d.pet_id, visit_id=d.visit_id,
                happened_on=d.happened_on, body=d.body,
                embedding=kept.embedding if kept is not None else vector,
                model=CURRENT_MODEL if kept is not None or vector is not None else None,
            ))
        # 임베딩을 못 받았으면 글만 넣고(글자로는 찾아진다) 줄을 남겨 뒤에 벡터를 채운다.
        return await self._settle(job, ctx, documents, finished=not fresh or embedded is not None)

    async def _settle(self, job: ReindexJob, ctx, documents: list[SearchDocument], *, finished: bool) -> bool:
        now = self._now()
        await self._documents.replace_target(ctx, job.scope, job.ref_id, documents, now)
        if finished:
            await self._queue.finish(job)
        else:
            await self._queue.retry_later(job, now)
        await self._commit()
        return finished
