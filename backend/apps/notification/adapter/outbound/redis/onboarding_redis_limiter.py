from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort

# 동작 → (한도, 창 초). 토큰·인증번호 요청은 시간당 5회, 토큰·인증번호 입력은 10분에 5회(설계 9.4).
_LIMITS: dict[str, tuple[int, int]] = {
    "token": (5, 3600),
    "sender_verification": (5, 3600),
    "link": (5, 600),
    "sender_confirm": (5, 600),
}

logger = logging.getLogger(__name__)


class OnboardingRedisLimiter(OnboardingLimiterPort):
    """키: notification:onboarding:{동작}:{shop_id} → 이번 창의 시도 횟수."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, shop_id: int, action: str) -> bool:
        limit, window = _LIMITS[action]
        key = f"notification:onboarding:{action}:{shop_id}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window, nx=True)  # 창은 처음 셀 때만 잡는다
                count, _ = await pipe.execute()
        except RedisError:
            logger.warning("온보딩 횟수 제한을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return True
        return int(count) <= limit
