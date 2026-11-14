"""search 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from search.adapter.outbound.pg.search_document_pg_repository import SearchDocumentPgRepository
from search.adapter.outbound.pg.search_job_pg_repository import SearchJobPgRepository
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.app.ports.output.search_document_repository import SearchDocumentRepository


def build_document_repository(db: AsyncSession) -> SearchDocumentRepository:
    return SearchDocumentPgRepository(db)


def build_queue_repository(db: AsyncSession) -> ReindexQueueRepository:
    return SearchJobPgRepository(db)
