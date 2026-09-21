"""Alembic 환경 — 비동기 엔진으로 마이그레이션을 실행한다. 오프라인 모드는 쓰지 않는다."""
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import orm_registry  # noqa: F401 — 메타데이터 등록
from core.config import DATABASE_URL
from core.database import Base

target_metadata = Base.metadata


def _database_url() -> str:
    """테스트 DB 준비 스크립트는 `-x db_url=…` 로 대상을 바꾼다. 없으면 개발 DB 다."""
    return context.get_x_argument(as_dictionary=True).get("db_url", DATABASE_URL)


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(_database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_async())
