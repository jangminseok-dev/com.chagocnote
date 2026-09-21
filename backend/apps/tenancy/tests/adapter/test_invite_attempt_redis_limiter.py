import pytest
from redis.asyncio import from_url

from core.config import REDIS_URL
from tenancy.adapter.outbound.redis.invite_attempt_redis_limiter import InviteAttemptRedisLimiter

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    client = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


async def test_시도할_때마다_횟수가_오른다(redis):
    limiter = InviteAttemptRedisLimiter(redis)
    assert [await limiter.hit(7) for _ in range(3)] == [1, 2, 3]


async def test_유저마다_따로_센다(redis):
    limiter = InviteAttemptRedisLimiter(redis)
    await limiter.hit(7)
    assert await limiter.hit(8) == 1


async def test_창은_첫_시도에서_60초로_잡히고_이후_시도가_늘리지_않는다(redis):
    limiter = InviteAttemptRedisLimiter(redis)
    await limiter.hit(7)
    await redis.expire("tenancy:invite-attempts:7", 30)
    await limiter.hit(7)
    assert 0 < await redis.ttl("tenancy:invite-attempts:7") <= 30
