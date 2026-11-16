from __future__ import annotations

import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from hub.app.ports.public_limiter_port import PublicLimiterPort

_HITS_PER_WINDOW = 60
_HIT_WINDOW_SECONDS = 60
_MISSES_PER_WINDOW = 20
_MISS_WINDOW_SECONDS = 600
_WRITES_PER_WINDOW = 10
_WRITE_WINDOW_SECONDS = 600

logger = logging.getLogger(__name__)


def _digest(client: str) -> str:
    """접속 주소는 헤더로 들어온 값일 수 있어 그대로 키에 넣지 않는다 — 길이가 정해진 해시로 바꾼다."""
    return hashlib.sha256(client.encode()).hexdigest()[:32]


class PublicRedisLimiter(PublicLimiterPort):
    """키: {이름 공간}-hits:{주소 해시} → 이번 1분 창의 요청 수, -misses: → 이번 10분 창의 실패 수, -writes: → 이번 10분 창의 제출 수.

    이름 공간은 알림장이 "visit:report", 서류가 "customer:form" 이다 — 서로의 수를 세지 않는다.
    """

    def __init__(self, redis: Redis, namespace: str) -> None:
        self._redis = redis
        self._namespace = namespace

    def _key(self, kind: str, client: str) -> str:
        return f"{self._namespace}-{kind}:{_digest(client)}"

    async def allow(self, client: str) -> bool:
        hits = self._key("hits", client)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(hits)
                pipe.expire(hits, _HIT_WINDOW_SECONDS, nx=True)  # 창은 처음 셀 때만 잡는다
                count, _ = await pipe.execute()
        except RedisError:
            logger.warning("알림장 횟수 제한을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return True
        return int(count) <= _HITS_PER_WINDOW

    async def note_miss(self, client: str) -> None:
        misses = self._key("misses", client)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(misses)
                pipe.expire(misses, _MISS_WINDOW_SECONDS, nx=True)
                await pipe.execute()
        except RedisError:
            logger.warning("알림장 조회 실패를 세지 못했습니다 — Redis 에 닿지 못했습니다.")

    async def missed_too_much(self, client: str) -> bool:
        misses = self._key("misses", client)
        try:
            missed = await self._redis.get(misses)
        except RedisError:
            logger.warning("알림장 실패 수 차단을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return False
        return int(missed or 0) >= _MISSES_PER_WINDOW

    async def allow_write(self, client: str) -> bool:
        writes = self._key("writes", client)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(writes)
                pipe.expire(writes, _WRITE_WINDOW_SECONDS, nx=True)
                count, _ = await pipe.execute()
        except RedisError:
            logger.warning("공개 제출의 횟수 제한을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return True
        return int(count) <= _WRITES_PER_WINDOW
