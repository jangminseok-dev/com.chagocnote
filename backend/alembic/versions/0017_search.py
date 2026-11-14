"""기록 검색 — 글 사본과 벡터(search_documents), 다시 색인할 줄(search_jobs), pgvector 확장 — ⑨-1

글의 원본은 visit·customer 의 것이다. 여기 있는 것은 언제든 다시 만들 수 있는 사본이다(scripts/reindex_search.py).
스포크를 넘는 외래 키는 걸지 않는다 — shop_id·customer_id·pet_id·visit_id 는 정수 칸이다.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-15
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

# 목록은 글자로 적는다 — tests/integration/test_search_schema.py 가 도메인 튜플과 같은지 실제 DB 로 본다.
_KINDS = "('care_note', 'internal_note', 'visit_memo', 'pet_memo', 'condition_note', 'customer_memo')"
_SCOPES = "('visit', 'pet', 'customer')"
_DIMENSIONS = 384   # intfloat/multilingual-e5-small


def upgrade() -> None:
    # 이미지(pgvector/pgvector:pg17)에 들어 있다. pg_trgm 은 0005 가 켰다.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "search_documents",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("source_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("pet_id", sa.BigInteger),
        sa.Column("visit_id", sa.BigInteger),
        sa.Column("happened_on", sa.Date),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("embedding", Vector(_DIMENSIONS)),
        sa.Column("model", sa.String(80)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("shop_id", "kind", "source_id", name="uq_search_documents_source"),
        sa.CheckConstraint("kind IN " + _KINDS, name="ck_search_documents_kind"),
        # 벡터와 그것을 만든 모델 이름은 함께 있거나 함께 없다.
        sa.CheckConstraint("(embedding IS NULL) = (model IS NULL)", name="ck_search_documents_embedding_model"),
    )
    op.create_index(
        "ix_search_documents_body_trgm", "search_documents", ["body"],
        postgresql_using="gin", postgresql_ops={"body": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_search_documents_embedding_hnsw", "search_documents", ["embedding"],
        postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_search_documents_shop_customer", "search_documents", ["shop_id", "customer_id"])
    op.create_index("ix_search_documents_shop_pet", "search_documents", ["shop_id", "pet_id"])

    op.create_table(
        "search_jobs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("scope", sa.String(10), nullable=False),
        sa.Column("ref_id", sa.BigInteger, nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generation", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column("attempts", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("shop_id", "scope", "ref_id", name="uq_search_jobs_target"),
        sa.CheckConstraint("scope IN " + _SCOPES, name="ck_search_jobs_scope"),
    )
    op.create_index("ix_search_jobs_next_attempt_at", "search_jobs", ["next_attempt_at"])


def downgrade() -> None:
    op.drop_table("search_jobs")
    op.drop_table("search_documents")
    op.execute("DROP EXTENSION IF EXISTS vector")
