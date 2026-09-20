"""pytest 루트 설정 — 통합 테스트용 공용 픽스처."""
from __future__ import annotations

import pytest

TEST_DB = "chagocnote_test"


@pytest.fixture
async def db_session():
    """별도 데이터베이스 chagocnote_test 에 붙은 세션. 테스트마다 테이블을 새로 만든다."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import auth.adapter.outbound.orm.user_orm  # noqa: F401 — 메타데이터 등록
    from core.config import DATABASE_URL
    from core.database import Base

    admin = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = (
            await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB}
            )
        ).scalar()
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    await admin.dispose()

    engine = create_async_engine(DATABASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as session:
        yield session
    await engine.dispose()
