"""search 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import EMBED_BASE_URL
from search.adapter.outbound.gateways.embed_http_gateway import EmbedHttpGateway, NoEmbedding
from search.adapter.outbound.pg.search_candidate_pg_repository import SearchCandidatePgRepository
from search.adapter.outbound.pg.search_document_pg_repository import SearchDocumentPgRepository
from search.adapter.outbound.pg.search_job_pg_repository import SearchJobPgRepository
from search.app.ports.output.embedding_port import EmbeddingPort
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.app.ports.output.search_candidate_repository import SearchCandidateRepository
from search.app.ports.output.search_document_repository import SearchDocumentRepository


def build_document_repository(db: AsyncSession) -> SearchDocumentRepository:
    return SearchDocumentPgRepository(db)


def build_queue_repository(db: AsyncSession) -> ReindexQueueRepository:
    return SearchJobPgRepository(db)


def build_candidate_repository(db: AsyncSession) -> SearchCandidateRepository:
    return SearchCandidatePgRepository(db)


_embedder: EmbeddingPort | None = None


def get_embedder() -> EmbeddingPort:
    """프로세스에 하나 — HTTP 클라이언트를 나눠 쓴다. 주소가 비면 뜻 검색 없이 돈다. 테스트는 monkeypatch 로 바꾼다."""
    global _embedder
    if _embedder is None:
        _embedder = EmbedHttpGateway(EMBED_BASE_URL) if EMBED_BASE_URL else NoEmbedding()
    return _embedder


def reset_embedder() -> None:
    """테스트용."""
    global _embedder
    _embedder = None
