"""수기로 쓴 마이그레이션과 ORM 이 같은 스키마를 말하는지 확인한다."""
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

import orm_registry  # noqa: F401 — 모든 ORM 을 메타데이터에 올린다
from core.database import Base

pytestmark = pytest.mark.integration


async def test_마이그레이션과_ORM_이_같은_스키마를_말한다(db_engine):
    async with db_engine.connect() as conn:
        diffs = await conn.run_sync(
            lambda sync_conn: compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)
        )
    assert diffs == []
