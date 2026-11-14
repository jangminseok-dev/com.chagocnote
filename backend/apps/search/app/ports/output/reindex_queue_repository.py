from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from search.domain.entities.search_document import ReindexJob


class ReindexQueueRepository(ABC):
    """다시 색인할 줄(search_jobs). 넣기는 매장 범위이고, 집기·끝내기·미루기는 색인기가 전 매장에 대해 하므로
    `ShopContext` 를 받지 않는다 — `NotificationQueueRepository` 와 같은 예외다."""

    @abstractmethod
    async def enqueue(self, ctx: ShopContext, scope: str, ref_id: int, now: datetime) -> None:
        """그 대상의 줄을 하나 넣는다. 이미 있으면 줄을 늘리지 않고 세대를 올리고, 시도 횟수를 0 으로, 다음 시각을
        지금으로 당긴다."""

    @abstractmethod
    async def claim_due(self, now: datetime, limit: int) -> list[ReindexJob]:
        """다음 시각이 된 줄을 오래된 것부터 limit 개 집는다(FOR UPDATE SKIP LOCKED). 집은 줄은 다음 시각을
        CLAIM_HOLD 만큼 뒤로 민다 — 부르는 쪽이 바로 커밋해 잠금을 놓는다."""

    @abstractmethod
    async def finish(self, job: ReindexJob) -> None:
        """줄을 지운다 — 세대가 집었을 때 그대로일 때만. 그 사이에 올랐으면 남긴다(바뀐 것을 다시 색인해야 한다)."""

    @abstractmethod
    async def retry_later(self, job: ReindexJob, now: datetime) -> None:
        """시도 횟수를 올리고 다음 시각을 retry_delay 만큼 뒤로 — 세대가 그대로일 때만. 올랐으면 그대로 둔다
        (이미 지금으로 당겨져 있다)."""
