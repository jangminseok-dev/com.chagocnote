"""가져가기의 원자성과 경합 — 실제 Postgres, 두 세션."""
import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.tests.helpers.builders import ctx, new_photo

pytestmark = pytest.mark.integration

A = ctx(shop_id=1)
BLOCKED = 0.5


async def _ready(session, count=1):
    repo = MediaPgRepository(session)
    ids = []
    for _ in range(count):
        media = await repo.create(A, new_photo())
        await repo.mark_ready(A, media.id, 100)
        ids.append(media.id)
    await session.commit()
    return ids


async def test_하나라도_못_가져가면_세이브포인트로_되돌리고_세션은_계속_쓴다(db_session):
    repo = MediaPgRepository(db_session)
    ready, = await _ready(db_session)
    pending = (await repo.create(A, new_photo())).id
    assert await repo.attach_all(A, [ready, pending]) is None
    assert (await repo.get(A, ready)).attached_at is None
    assert await repo.attach_all(A, [ready]) == {ready: "photo"}


async def test_같은_미디어를_동시에_가져가면_늦은_쪽은_못_가져간다(db_engine, db_session):
    """조건부 UPDATE 의 attached_at IS NULL 을 빼면 늦은 쪽도 가져가 한 객체가 두 기록에 붙는다."""
    media_id, = await _ready(db_session)
    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        assert await MediaPgRepository(first).attach_all(A, [media_id]) == {media_id: "photo"}
        late = asyncio.create_task(MediaPgRepository(second).attach_all(A, [media_id]))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await first.commit()
        assert await late is None
