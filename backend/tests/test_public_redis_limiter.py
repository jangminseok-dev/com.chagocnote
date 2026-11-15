import hashlib
import logging

import pytest
from redis.asyncio import from_url
from redis.exceptions import ConnectionError as RedisConnectionError

from core.config import REDIS_URL
from core.public_redis_limiter import PublicRedisLimiter

pytestmark = pytest.mark.integration

CLIENT = "203.0.113.7"


def _key(name: str, client: str = CLIENT) -> str:
    return f"visit:report-{name}:{hashlib.sha256(client.encode()).hexdigest()[:32]}"


@pytest.fixture
async def redis():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    client = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


async def test_1분에_60번까지_받고_61번째부터_막는다(redis):
    """R1"""
    limiter = PublicRedisLimiter(redis, "visit:report")
    assert [await limiter.allow(CLIENT) for _ in range(62)] == [True] * 60 + [False, False]


async def test_실패가_20번_쌓여도_allow_는_막지_않는다(redis):
    """검토 지적 — 실패 수는 allow 가 아니라 missed_too_much 가 본다. 서명이 맞는 토큰은 남의 실패로 막히지 않는다."""
    limiter = PublicRedisLimiter(redis, "visit:report")
    for _ in range(20):
        await limiter.note_miss(CLIENT)
    assert await limiter.allow(CLIENT) is True


async def test_실패가_19번까지는_차지_않고_20번이면_찼다(redis):
    """R1"""
    limiter = PublicRedisLimiter(redis, "visit:report")
    for _ in range(19):
        await limiter.note_miss(CLIENT)
    assert await limiter.missed_too_much(CLIENT) is False
    await limiter.note_miss(CLIENT)
    assert await limiter.missed_too_much(CLIENT) is True


async def test_접속_주소마다_따로_센다(redis):
    limiter = PublicRedisLimiter(redis, "visit:report")
    for _ in range(61):
        await limiter.allow(CLIENT)
    for _ in range(20):
        await limiter.note_miss("198.51.100.9")
    assert await limiter.allow("192.0.2.1") is True
    assert (await redis.get(_key("hits", "192.0.2.1")), await redis.get(_key("misses", "192.0.2.1"))) == ("1", None)
    assert await limiter.missed_too_much("198.51.100.9") is True
    assert await limiter.missed_too_much("192.0.2.1") is False


async def test_창은_처음_셀_때_잡히고_이후_요청이_늘리지_않는다(redis):
    limiter = PublicRedisLimiter(redis, "visit:report")
    await limiter.allow(CLIENT)
    await limiter.note_miss(CLIENT)
    assert 0 < await redis.ttl(_key("hits")) <= 60
    assert 60 < await redis.ttl(_key("misses")) <= 600
    await redis.expire(_key("hits"), 30)
    await redis.expire(_key("misses"), 30)
    await limiter.allow(CLIENT)
    await limiter.note_miss(CLIENT)
    assert 0 < await redis.ttl(_key("hits")) <= 30
    assert 0 < await redis.ttl(_key("misses")) <= 30


async def test_창이_지나면_다시_받는다(redis):
    """기다리지 않는다 — 창이 끝난 것은 키가 사라진 것이다."""
    limiter = PublicRedisLimiter(redis, "visit:report")
    for _ in range(61):
        await limiter.allow(CLIENT)
    for _ in range(20):
        await limiter.note_miss(CLIENT)
    assert await limiter.allow(CLIENT) is False           # 요청 수 창이 아직 남아 있다
    await redis.delete(_key("hits"))
    assert await limiter.allow(CLIENT) is True             # 요청 수 창이 지났다 — 새로 시작한다
    assert await limiter.missed_too_much(CLIENT) is True   # 실패의 창은 따로 있다 — 아직 남아 있다
    await redis.delete(_key("misses"))
    assert await limiter.missed_too_much(CLIENT) is False


async def test_아주_긴_접속_주소도_키는_짧다(redis):
    limiter = PublicRedisLimiter(redis, "visit:report")
    await limiter.allow("1" * 5000)
    await limiter.note_miss("1" * 5000)
    keys = sorted(await redis.keys("*"))
    assert keys == [_key("hits", "1" * 5000), _key("misses", "1" * 5000)]
    assert all(len(k) < 64 and "1" * 40 not in k for k in keys)


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

    async def get(self, *args, **kwargs):
        raise RedisConnectionError("Error connecting to redis:6379")


async def test_Redis_에_닿지_못하면_통과시키고_경고를_남긴다(caplog):
    limiter = PublicRedisLimiter(_DeadRedis(), "visit:report")
    with caplog.at_level(logging.WARNING):
        assert await limiter.allow(CLIENT) is True
        await limiter.note_miss(CLIENT)
        assert await limiter.missed_too_much(CLIENT) is False
    assert [r.levelname for r in caplog.records] == ["WARNING", "WARNING", "WARNING"]
    assert CLIENT not in caplog.text


async def test_쓰기_제한은_10분에_10번까지다(redis):
    limiter = PublicRedisLimiter(redis, "customer:form")
    assert [await limiter.allow_write(CLIENT) for _ in range(11)] == [True] * 10 + [False]
    assert 0 < await redis.ttl(f"customer:form-writes:{hashlib.sha256(CLIENT.encode()).hexdigest()[:32]}") <= 600


async def test_이름_공간이_다르면_서로의_수를_세지_않는다(redis):
    report, form = PublicRedisLimiter(redis, "visit:report"), PublicRedisLimiter(redis, "customer:form")
    for _ in range(60):
        await report.allow(CLIENT)
    assert await report.allow(CLIENT) is False
    assert await form.allow(CLIENT) is True


async def test_Redis_에_닿지_못하면_쓰기도_막지_않는다():
    assert await PublicRedisLimiter(_DeadRedis(), "customer:form").allow_write(CLIENT) is True
