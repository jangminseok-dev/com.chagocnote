import asyncio

import pytest
from redis.asyncio import from_url

from auth.adapter.outbound.redis.refresh_token_redis_store import RefreshTokenRedisStore
from auth.domain.value_objects.refresh_lookup import RefreshStatus
from core.config import REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture
async def store():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    redis = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await redis.flushdb()
    yield RefreshTokenRedisStore(redis, ttl_seconds=60)
    await redis.flushdb()
    await redis.aclose()


async def test_저장한_토큰은_한_번만_꺼낼_수_있다(store):
    await store.save("token-a", user_id=7)
    first = await store.take("token-a")
    assert (first.status, first.user_id) == (RefreshStatus.ACTIVE, 7)
    second = await store.take("token-a")
    assert (second.status, second.user_id) == (RefreshStatus.USED, 7)


async def test_모르는_토큰은_MISSING_이다(store):
    lookup = await store.take("never-issued")
    assert (lookup.status, lookup.user_id) == (RefreshStatus.MISSING, None)


async def test_폐기한_토큰은_MISSING_이다(store):
    await store.save("token-b", user_id=7)
    await store.revoke("token-b")
    assert (await store.take("token-b")).status is RefreshStatus.MISSING


async def test_유저의_모든_세션을_폐기한다(store):
    await store.save("token-c", user_id=7)
    await store.save("token-d", user_id=7)
    await store.save("token-e", user_id=8)
    await store.revoke_all(7)
    assert (await store.take("token-c")).status is RefreshStatus.MISSING
    assert (await store.take("token-d")).status is RefreshStatus.MISSING
    assert (await store.take("token-e")).status is RefreshStatus.ACTIVE


async def test_토큰_원문은_Redis_키에_남지_않는다(store):
    await store.save("plain-token-value", user_id=7)
    keys = [k async for k in store._redis.scan_iter("*")]
    assert keys and all("plain-token-value" not in k for k in keys)


async def test_동시에_같은_토큰을_꺼내면_하나는_ACTIVE_다른_하나는_USED_다(store):
    await store.save("token-f", user_id=7)
    first, second = await asyncio.gather(store.take("token-f"), store.take("token-f"))
    assert sorted((first.status, second.status), key=lambda s: s.value) == [
        RefreshStatus.ACTIVE,
        RefreshStatus.USED,
    ]
    assert first.user_id == 7 and second.user_id == 7
