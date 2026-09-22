"""엔진이 SQLAlchemy 오류 문자열에 바인드 파라미터(이름·전화·메모)를 남기지 않는지 확인한다."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

import core.database

pytestmark = pytest.mark.integration


async def test_엔진은_DBAPIError_문자열에_바인드_값을_남기지_않는다(migrated_test_db, monkeypatch):
    monkeypatch.setattr(core.database, "DATABASE_URL", migrated_test_db)
    monkeypatch.setattr(core.database, "engine", None)
    monkeypatch.setattr(core.database, "_session_factory", None)
    core.database.init_engine()
    engine = core.database.engine
    assert engine is not None
    assert engine.sync_engine.hide_parameters is True

    secret = "\x00몰래이름"  # NUL 은 asyncpg 가 텍스트로 못 보내 DBAPIError 가 난다
    try:
        async with engine.connect() as conn:
            with pytest.raises(DBAPIError) as caught:
                await conn.execute(text("SELECT :val AS x"), {"val": secret})
        assert "몰래이름" not in str(caught.value)
    finally:
        await core.database.dispose_engine()
