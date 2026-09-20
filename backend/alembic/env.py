"""Alembic 환경 — 비동기 엔진으로 마이그레이션을 실행한다. 오프라인 모드는 쓰지 않는다."""
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import auth.adapter.outbound.orm.user_orm  # noqa: F401 — 메타데이터 등록
from core.config import DATABASE_URL
from core.database import Base

target_metadata = Base.metadata


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_async())
