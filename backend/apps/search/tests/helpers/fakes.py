"""search 의 공용 스텁 — 포트 ABC 를 상속한다(test_fakes_are_ports)."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from hub.app.dtos.search_source import SourceDocument
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.search_source_port import SearchSourcePort
from hub.app.ports.shop_profile_port import ShopProfilePort
from search.app.ports.output.embedding_port import DIMENSIONS, Embedded, EmbeddingPort
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.app.ports.output.search_document_repository import SearchDocumentRepository
from search.domain.entities.search_document import ReindexJob, SearchDocument
from search.domain.services.embedding_model import CURRENT_MODEL
from search.domain.services.retry import CLAIM_HOLD, retry_delay
from search.domain.services.targets import belongs


class FakeDocuments(SearchDocumentRepository):
    """{(매장, kind, source_id): 문서}. writes 는 replace_target 이 불린 (scope, ref_id) 의 기록이다."""

    def __init__(self, journal: list | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.rows: dict[tuple[int, str, int], SearchDocument] = {}
        self.writes: list[tuple[str, int]] = []

    def seed(self, shop_id: int, *documents: SearchDocument) -> None:
        for d in documents:
            self.rows[(shop_id, d.kind, d.source_id)] = d

    def of_shop(self, shop_id: int) -> list[SearchDocument]:
        return [d for (shop, _, _), d in self.rows.items() if shop == shop_id]

    async def list_for_target(self, ctx, scope, ref_id):
        self.journal.append(("read_stored", scope, ref_id))
        return [d for d in self.of_shop(ctx.shop_id) if belongs(d, scope, ref_id)]

    async def replace_target(self, ctx, scope, ref_id, documents, now):
        if not all(belongs(d, scope, ref_id) for d in documents):
            raise ValueError("그 대상의 문서가 아닙니다.")
        self.writes.append((scope, ref_id))
        self.journal.append(("replace", scope, ref_id, len(documents)))
        for key in [k for k, d in self.rows.items() if k[0] == ctx.shop_id and belongs(d, scope, ref_id)]:
            del self.rows[key]
        self.seed(ctx.shop_id, *documents)

    async def delete_for_customer(self, ctx, customer_id):
        for key in [k for k, d in self.rows.items() if k[0] == ctx.shop_id and d.customer_id == customer_id]:
            del self.rows[key]


class FakeQueue(ReindexQueueRepository):
    """줄의 목록. due 는 {줄 ID: 다음 시각}."""

    def __init__(self) -> None:
        self.jobs: dict[int, ReindexJob] = {}
        self.due: dict[int, datetime] = {}
        self._next_id = 1

    def targets(self) -> list[tuple[int, str, int]]:
        return [(j.shop_id, j.scope, j.ref_id) for j in self.jobs.values()]

    async def enqueue(self, ctx, scope, ref_id, now):
        for job in self.jobs.values():
            if (job.shop_id, job.scope, job.ref_id) == (ctx.shop_id, scope, ref_id):
                self.jobs[job.id] = replace(job, generation=job.generation + 1, attempts=0)
                self.due[job.id] = now
                return
        job = ReindexJob(id=self._next_id, shop_id=ctx.shop_id, scope=scope, ref_id=ref_id, generation=1, attempts=0)
        self._next_id += 1
        self.jobs[job.id], self.due[job.id] = job, now

    async def claim_due(self, now, limit):
        picked = sorted((j for j in self.jobs.values() if self.due[j.id] <= now),
                        key=lambda j: (self.due[j.id], j.id))[:limit]
        for job in picked:
            self.due[job.id] = now + CLAIM_HOLD
        return picked

    async def finish(self, job):
        current = self.jobs.get(job.id)
        if current is not None and current.generation == job.generation:
            del self.jobs[job.id], self.due[job.id]

    async def retry_later(self, job, now):
        current = self.jobs.get(job.id)
        if current is not None and current.generation == job.generation:
            self.jobs[job.id] = replace(current, attempts=current.attempts + 1)
            self.due[job.id] = now + retry_delay(current.attempts)


class FakeEmbedder(EmbeddingPort):
    """EmbeddingPort 스텁 — 글마다 정해진 벡터를 준다. down 이면 None(임베딩 프로세스가 죽었다).

    calls 는 받은 (kind, 글 목록). during 은 임베딩이 도는 사이에 끼어드는 일을 흉내 낸다(인자 없는 async 함수).
    """

    def __init__(self, journal: list | None = None, model: str = CURRENT_MODEL) -> None:
        self.journal = journal if journal is not None else []
        self.model = model
        self.down = False
        self.calls: list[tuple[str, list[str]]] = []
        self.during = None

    @staticmethod
    def vector_of(text: str) -> tuple[float, ...]:
        """글의 길이로 정해지는 벡터 — 어느 글의 벡터인지 테스트가 알아볼 수 있게."""
        return (float(len(text)),) + (0.0,) * (DIMENSIONS - 1)

    async def embed(self, kind, texts, timeout):
        self.calls.append((kind, list(texts)))
        self.journal.append(("embed", len(texts)))
        if self.during is not None:
            await self.during()
        if self.down:
            return None
        return Embedded(model=self.model, vectors=tuple(self.vector_of(t) for t in texts))


class FakeSource(SearchSourcePort):
    """SearchSourcePort 스텁 — {(매장, scope, ref_id): 문서 목록}. seen 은 받은 컨텍스트들."""

    def __init__(self, journal: list | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.rows: dict[tuple[int, str, int], list[SourceDocument]] = {}
        self.seen: list = []
        self.fail_for: set[int] = set()   # 이 ref_id 를 읽으면 던진다

    def put(self, shop_id: int, scope: str, ref_id: int, *documents: SourceDocument) -> None:
        self.rows[(shop_id, scope, ref_id)] = list(documents)

    async def documents(self, ctx, scope, ref_id):
        self.seen.append(ctx)
        self.journal.append(("read_source", scope, ref_id))
        if ref_id in self.fail_for:
            raise RuntimeError("원본 읽기 실패")
        return list(self.rows.get((ctx.shop_id, scope, ref_id), []))


class FakeShops(ShopProfilePort):
    """ShopProfilePort 스텁 — 있는 매장 ID 와 시간대."""

    def __init__(self, timezones: dict[int, str] | None = None) -> None:
        self.timezones = timezones if timezones is not None else {1: "Asia/Seoul", 2: "Asia/Seoul"}

    async def public_profile(self, shop_id):
        if shop_id not in self.timezones:
            return None
        return ShopProfile(shop_id=shop_id, name="매장", phone=None, address=None,
                           timezone=self.timezones[shop_id], open=True)
