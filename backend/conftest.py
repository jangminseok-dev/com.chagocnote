"""pytest 루트 설정 — 통합 테스트용 공용 픽스처."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# 마이그레이션이 넣은 시드(역할·권한)와 버전 표는 테스트 사이에 비우지 않는다.
_KEEP_TABLES = {"alembic_version", "roles", "permissions", "role_permissions"}


@pytest.fixture(scope="session")
def migrated_test_db() -> str:
    """별도 데이터베이스 chagocnote_test 를 alembic upgrade head 로 다시 만든다. 세션에 한 번."""
    from scripts.prepare_test_db import TEST_DATABASE_URL

    subprocess.run(
        [sys.executable, "scripts/prepare_test_db.py"], check=True, cwd=Path(__file__).parent
    )
    return TEST_DATABASE_URL


@pytest.fixture
async def db_engine(migrated_test_db):
    """테스트 DB 에 붙은 엔진. 테스트마다 시드 표를 뺀 모든 표를 비운다."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(migrated_test_db)
    async with engine.begin() as conn:
        names = (
            await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        ).scalars()
        targets = [f'"{name}"' for name in names if name not in _KEEP_TABLES]
        if targets:
            await conn.execute(
                text("TRUNCATE " + ", ".join(targets) + " RESTART IDENTITY CASCADE")
            )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async with async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)() as session:
        yield session
