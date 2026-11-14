from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from search.app.dtos.enqueue_reindex_dto import EnqueueReindexCommand
from search.app.ports.input.enqueue_reindex_use_case import EnqueueReindexUseCase
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.domain.services.targets import target_filter


class EnqueueReindexInteractor(EnqueueReindexUseCase):
    """글이 바뀐 대상을 다시 색인할 줄에 넣는다. 발행한 쓰기와 같은 트랜잭션에서 돈다 — 줄 하나만 쓰고, 원본을
    읽지도 임베딩하지도 않는다(저장이 느려지지 않게, ⑨ 설계 3.4)."""

    def __init__(self, queue: ReindexQueueRepository, now: Callable[[], datetime]) -> None:
        self._queue = queue
        self._now = now

    async def enqueue_reindex(self, command: EnqueueReindexCommand) -> None:
        target_filter(command.scope)   # 모르는 대상이면 여기서 멈춘다
        await self._queue.enqueue(command.ctx, command.scope, command.ref_id, self._now())
