from __future__ import annotations

from redis.asyncio import Redis

from tenancy.app.ports.output.invite_attempt_limiter_port import InviteAttemptLimiterPort

_WINDOW_SECONDS = 60


class InviteAttemptRedisLimiter(InviteAttemptLimiterPort):
    """키: tenancy:invite-attempts:{user_id} → 이번 1분 창의 시도 횟수."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, user_id: int) -> int:
        key = f"tenancy:invite-attempts:{user_id}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, _WINDOW_SECONDS, nx=True)  # 창은 첫 시도에서만 잡는다
            count, _ = await pipe.execute()
        return int(count)
