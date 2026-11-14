from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from search.domain.entities.search_document import KINDS, SCOPES

EMBEDDING_DIMENSIONS = 384   # intfloat/multilingual-e5-small — 모델을 바꾸면 마이그레이션과 함께 바꾼다


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


class SearchDocumentOrm(Base):
    """검색되는 글 하나의 사본과 벡터(⑨ 설계 3.3). 원본은 visit·customer 의 것이다 — 외래 키를 걸지 않는다."""

    __tablename__ = "search_documents"
    __table_args__ = (
        UniqueConstraint("shop_id", "kind", "source_id", name="uq_search_documents_source"),
        CheckConstraint(_in("kind", KINDS), name="ck_search_documents_kind"),
        CheckConstraint("(embedding IS NULL) = (model IS NULL)", name="ck_search_documents_embedding_model"),
        Index("ix_search_documents_body_trgm", "body", postgresql_using="gin", postgresql_ops={"body": "gin_trgm_ops"}),
        Index(
            "ix_search_documents_embedding_hnsw", "embedding",
            postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_search_documents_shop_customer", "shop_id", "customer_id"),
        Index("ix_search_documents_shop_pet", "shop_id", "pet_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(BigInteger)
    pet_id: Mapped[int | None] = mapped_column(BigInteger)
    visit_id: Mapped[int | None] = mapped_column(BigInteger)
    happened_on: Mapped[date | None] = mapped_column(Date)
    body: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    model: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SearchJobOrm(Base):
    """다시 색인할 대상의 줄. 같은 대상은 한 줄이다 — 다시 바뀌면 generation 이 오른다."""

    __tablename__ = "search_jobs"
    __table_args__ = (
        UniqueConstraint("shop_id", "scope", "ref_id", name="uq_search_jobs_target"),
        CheckConstraint(_in("scope", SCOPES), name="ck_search_jobs_scope"),
        Index("ix_search_jobs_next_attempt_at", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    scope: Mapped[str] = mapped_column(String(10))
    ref_id: Mapped[int] = mapped_column(BigInteger)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generation: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
