"""통합 테스트용 데이터베이스 chagocnote_test 를 비우고 마이그레이션으로 다시 만든다.

pytest 가 세션에 한 번 하위 프로세스로 실행한다 (conftest.py 의 migrated_test_db).
하위 프로세스로 돌리는 이유: alembic/env.py 가 asyncio.run 을 쓰므로 pytest 의 이벤트 루프와 섞이면 안 된다.
직접 돌릴 수도 있다: cd infra && docker compose run --rm backend python scripts/prepare_test_db.py
"""
from __future__ import annotations

import asyncio

from alembic.config import main as alembic_main
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import DATABASE_URL

TEST_DB = "chagocnote_test"
TEST_DATABASE_URL = DATABASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB


async def _reset() -> None:
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

    engine = create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


def main() -> None:
    asyncio.run(_reset())
    alembic_main(["-x", f"db_url={TEST_DATABASE_URL}", "upgrade", "head"])


if __name__ == "__main__":
    main()
