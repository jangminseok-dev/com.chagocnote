from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# take() 는 "활성 키를 읽고 지우고 사용됨 키를 쓰는" 세 동작을 한 번에 해야 한다.
# 두 요청이 같은 토큰으로 동시에 들어오면(탈취 재사용 시나리오) 별도 왕복으로는
# 둘째 요청이 두 키를 모두 못 보고 MISSING 으로 오판될 수 있어 재사용 감지가 깨진다.
_TAKE_SCRIPT = """
local active_key = KEYS[1]
local used_key = KEYS[2]
local ttl = ARGV[1]
local user_set_prefix = ARGV[2]
local digest = ARGV[3]

local value = redis.call("GETDEL", active_key)
if value then
    redis.call("SET", used_key, value, "EX", ttl)
    redis.call("SREM", user_set_prefix .. value, digest)
    return {"active", value}
end

local used_value = redis.call("GET", used_key)
if used_value then
    return {"used", used_value}
end

return false
"""


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
        result = await self._redis.eval(
            _TAKE_SCRIPT,
            2,
            f"auth:refresh:{digest}",
            f"auth:refresh:used:{digest}",
            self._ttl,
            "auth:refresh:user:",
            digest,
        )
        if not result:
            return RefreshLookup(RefreshStatus.MISSING, None)
        status, value = result
        return RefreshLookup(
            RefreshStatus.ACTIVE if status == "active" else RefreshStatus.USED, int(value)
        )

    async def revoke(self, token: str) -> None:
        digest = _digest(token)
        value = await self._redis.getdel(f"auth:refresh:{digest}")
        if value is not None:
            await self._redis.srem(f"auth:refresh:user:{int(value)}", digest)

    async def revoke_all(self, user_id: int) -> None:
        digests = await self._redis.smembers(f"auth:refresh:user:{user_id}")
        keys = [f"auth:refresh:{d}" for d in digests] + [f"auth:refresh:user:{user_id}"]
        await self._redis.delete(*keys)
