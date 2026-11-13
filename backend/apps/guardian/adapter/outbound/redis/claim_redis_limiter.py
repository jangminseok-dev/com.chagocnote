from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort

LIMIT, WINDOW_SECONDS = 10, 3600

logger = logging.getLogger(__name__)


class ClaimRedisLimiter(ClaimLimiterPort):
    """키: guardian:claim:{user_id} → 이번 창의 시도 횟수."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, user_id: int) -> bool:
        key = f"guardian:claim:{user_id}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, WINDOW_SECONDS, nx=True)  # 창은 처음 셀 때만 잡는다
                count, _ = await pipe.execute()
        except RedisError:
            logger.warning("잇기 횟수 제한을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return True
        return int(count) <= LIMIT
