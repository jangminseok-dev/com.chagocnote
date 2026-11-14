from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.search_index_port import SearchIndexPort
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.app.ports.output.search_document_repository import SearchDocumentRepository
from search.app.services.indexer_wakeup import wake


class ForgetCustomerInteractor(SearchIndexPort):
    """허브의 SearchIndexPort 구현(HTTP 표면 없음). 익명화의 트랜잭션 안에서 그 고객의 글 사본을 곧바로 지운다 —
    색인기를 기다리는 동안 익명화한 고객의 글이 검색에 남지 않게(⑨ 설계 3.5)."""

    def __init__(
        self, documents: SearchDocumentRepository, queue: ReindexQueueRepository, now: Callable[[], datetime]
    ) -> None:
        self._documents = documents
        self._queue = queue
        self._now = now

    async def forget_customer(self, ctx: ShopContext, customer_id: int) -> None:
        await self._documents.delete_for_customer(ctx, customer_id)
        # 지금 색인기가 이 고객의 글을 임베딩하고 있을 수 있다 — 뒤에서 한 번 더 맞춘다.
        await self._queue.enqueue(ctx, "customer", customer_id, self._now())
        wake()   # 색인기가 반 초 뒤(익명화의 커밋 뒤) 돈다
