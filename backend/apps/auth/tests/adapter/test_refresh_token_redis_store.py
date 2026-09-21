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


async def _save(store, token, user_id):
    await store.save(token, user_id, await store.current_generation(user_id))


async def test_저장한_토큰은_한_번만_꺼낼_수_있다(store):
    await _save(store, "7.token-a", 7)
    first = await store.take("7.token-a")
    assert (first.status, first.user_id, first.generation) == (RefreshStatus.ACTIVE, 7, 0)
    second = await store.take("7.token-a")
    assert (second.status, second.user_id) == (RefreshStatus.USED, 7)


async def test_모르는_토큰과_모양이_다른_토큰은_MISSING_이다(store):
    for token in ("7.never-issued", "no-user-prefix"):
        lookup = await store.take(token)
        assert (lookup.status, lookup.user_id) == (RefreshStatus.MISSING, None)


async def test_폐기한_토큰은_MISSING_이다(store):
    await _save(store, "7.token-b", 7)
    await store.revoke("7.token-b")
    assert (await store.take("7.token-b")).status is RefreshStatus.MISSING


async def test_유저의_모든_세션을_폐기하면_세대가_오른다(store):
    await _save(store, "7.token-c", 7)
    await _save(store, "7.token-d", 7)
    await _save(store, "8.token-e", 8)
    await store.revoke_all(7)
    assert await store.current_generation(7) == 1
    assert (await store.take("7.token-c")).status is RefreshStatus.MISSING
    assert (await store.take("7.token-d")).status is RefreshStatus.MISSING
    assert (await store.take("8.token-e")).status is RefreshStatus.ACTIVE


async def test_폐기한_뒤에_새로_저장한_토큰은_쓸_수_있다(store):
    await store.revoke_all(7)
    await _save(store, "7.token-f", 7)
    lookup = await store.take("7.token-f")
    assert (lookup.status, lookup.generation) == (RefreshStatus.ACTIVE, 1)


async def test_세션_폐기와_경합한_새_토큰은_쓸_수_없다(store):
    """A1 — 갱신이 토큰을 꺼낸 뒤, 새 토큰을 저장하기 전에 모든 세션 폐기가 끼어든다."""
    await _save(store, "7.old", 7)
    taken = await store.take("7.old")          # 갱신 요청이 세대 0 으로 꺼냈다
    await store.revoke_all(7)                  # 그 사이 재사용 감지(또는 탈퇴)가 세션을 모두 끊었다
    await store.save("7.new", 7, taken.generation)   # 갱신 요청이 뒤늦게 새 토큰을 저장한다
    assert (await store.take("7.new")).status is RefreshStatus.MISSING


async def test_폐기된_세대의_옛_토큰은_재사용_신호가_아니다(store):
    """A2 — 옛 세대의 used 토큰을 다시 보내도 재로그인한 세션을 또 끊지 않는다."""
    await _save(store, "7.stolen", 7)
    await store.take("7.stolen")
    await store.revoke_all(7)
    assert (await store.take("7.stolen")).status is RefreshStatus.MISSING


async def test_앞의_유저_ID_를_바꾼_토큰은_MISSING_이다(store):
    """A3 — 키가 토큰 전체의 해시라, 앞을 바꾸면 저장된 키와 어긋난다."""
    await _save(store, "7.token-g", 7)
    assert (await store.take("8.token-g")).status is RefreshStatus.MISSING
    assert (await store.take("7.token-g")).status is RefreshStatus.ACTIVE


async def test_토큰_원문은_Redis_키에도_값에도_남지_않는다(store):
    await _save(store, "7.plain-token-value", 7)
    keys = [k async for k in store._redis.scan_iter("*")]
    values = [await store._redis.get(k) for k in keys]
    assert keys and all("plain-token-value" not in item for item in keys + values)


async def test_동시에_같은_토큰을_꺼내면_하나는_ACTIVE_다른_하나는_USED_다(store):
    await _save(store, "7.token-h", 7)
    first, second = await asyncio.gather(store.take("7.token-h"), store.take("7.token-h"))
    assert sorted((first.status, second.status), key=lambda s: s.value) == [
        RefreshStatus.ACTIVE,
        RefreshStatus.USED,
    ]
