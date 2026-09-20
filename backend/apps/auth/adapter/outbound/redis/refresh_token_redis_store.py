from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRedisStore(RefreshTokenStorePort):
    """키 구성
    auth:refresh:{해시}        → user_id   (유효한 토큰)
    auth:refresh:used:{해시}   → user_id   (이미 쓴 토큰의 흔적 — 재사용 감지용)
    auth:refresh:user:{id}     → 해시 집합 (유저의 모든 세션 폐기용)
    토큰 원문은 저장하지 않는다.
    """

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def save(self, token: str, user_id: int) -> None:
        digest = _digest(token)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(f"auth:refresh:{digest}", user_id, ex=self._ttl)
            pipe.sadd(f"auth:refresh:user:{user_id}", digest)
            pipe.expire(f"auth:refresh:user:{user_id}", self._ttl)
            await pipe.execute()

    async def take(self, token: str) -> RefreshLookup:
        digest = _digest(token)
        value = await self._redis.getdel(f"auth:refresh:{digest}")
        if value is not None:
            user_id = int(value)
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.set(f"auth:refresh:used:{digest}", user_id, ex=self._ttl)
                pipe.srem(f"auth:refresh:user:{user_id}", digest)
                await pipe.execute()
            return RefreshLookup(RefreshStatus.ACTIVE, user_id)
        used = await self._redis.get(f"auth:refresh:used:{digest}")
        if used is not None:
            return RefreshLookup(RefreshStatus.USED, int(used))
        return RefreshLookup(RefreshStatus.MISSING, None)

    async def revoke(self, token: str) -> None:
        digest = _digest(token)
        value = await self._redis.getdel(f"auth:refresh:{digest}")
        if value is not None:
            await self._redis.srem(f"auth:refresh:user:{int(value)}", digest)

    async def revoke_all(self, user_id: int) -> None:
        digests = await self._redis.smembers(f"auth:refresh:user:{user_id}")
        keys = [f"auth:refresh:{d}" for d in digests] + [f"auth:refresh:user:{user_id}"]
        await self._redis.delete(*keys)
