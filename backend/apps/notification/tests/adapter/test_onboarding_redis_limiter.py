"""온보딩 횟수 제한(설계 9.4, N3·N4) — 동작마다 창과 한도가 따로다. Redis 에 닿지 못하면 통과시키고 경고만 남긴다."""
import logging

import pytest
from redis.asyncio import from_url
from redis.exceptions import ConnectionError as RedisConnectionError

from core.config import REDIS_URL
from notification.adapter.outbound.redis.onboarding_redis_limiter import OnboardingRedisLimiter

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    client = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.mark.parametrize("action", ["token", "link", "sender_verification", "sender_confirm"])
async def test_동작마다_5번까지_받고_6번째부터_막는다(redis, action):
    limiter = OnboardingRedisLimiter(redis)
    assert [await limiter.allow(7, action) for _ in range(7)] == [True] * 5 + [False, False]


@pytest.mark.parametrize("action, window", [
    ("token", 3600), ("sender_verification", 3600), ("link", 600), ("sender_confirm", 600),
])
async def test_키는_동작과_매장으로_나뉘고_창은_처음_셀_때만_잡힌다(redis, action, window):
    limiter = OnboardingRedisLimiter(redis)
    await limiter.allow(7, action)
    key = f"notification:onboarding:{action}:7"
    assert await redis.get(key) == "1" and window - 5 < await redis.ttl(key) <= window
    await redis.expire(key, 30)
    await limiter.allow(7, action)
    assert await redis.get(key) == "2" and 0 < await redis.ttl(key) <= 30


async def test_매장마다_동작마다_따로_센다(redis):
    limiter = OnboardingRedisLimiter(redis)
    for _ in range(6):
        await limiter.allow(7, "token")
    assert await limiter.allow(8, "token") is True
    assert await limiter.allow(7, "link") is True
    assert await limiter.allow(7, "token") is False


async def test_창이_지나면_다시_받는다(redis):
    """기다리지 않는다 — 창이 끝난 것은 키가 사라진 것이다."""
    limiter = OnboardingRedisLimiter(redis)
    for _ in range(6):
        await limiter.allow(7, "link")
    assert await limiter.allow(7, "link") is False
    await redis.delete("notification:onboarding:link:7")
    assert await limiter.allow(7, "link") is True


class _DeadRedis:
    """닿지 않는 Redis — 명령을 실행하는 순간 연결 오류가 난다."""

    def pipeline(self, transaction=True):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __getattr__(self, name):
        return lambda *args, **kwargs: None

    async def execute(self):
        raise RedisConnectionError("Error connecting to redis:6379")


async def test_Redis_에_닿지_못하면_통과시키고_경고를_남긴다(caplog):
    limiter = OnboardingRedisLimiter(_DeadRedis())
    with caplog.at_level(logging.WARNING):
        assert await limiter.allow(7, "token") is True
    assert [r.levelname for r in caplog.records] == ["WARNING"]
