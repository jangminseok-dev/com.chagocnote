from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.domain.services.refresh_token_factory import refresh_token_user_id
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# take() 는 "활성 키를 읽고 지우고, 세대를 확인하고, 사용됨 흔적을 쓰는" 일을 한 번에 해야 한다.
# 두 요청이 같은 토큰으로 동시에 들어와도 하나만 active 를 받는다.
# 키는 전부 KEYS 로 받는다 (토큰 앞의 유저 ID 덕분에 미리 알 수 있다).
_TAKE_SCRIPT = """
local stored = redis.call("GETDEL", KEYS[1])
local current = redis.call("GET", KEYS[3]) or "0"
if stored then
    if stored ~= current then
        return {"missing"}
    end
    redis.call("SET", KEYS[2], stored, "EX", ARGV[1])
    return {"active", stored}
end
local used = redis.call("GET", KEYS[2])
if used and used == current then
    return {"used"}
end
return {"missing"}
"""


class RefreshTokenRedisStore(RefreshTokenStorePort):
    """키 구성
    auth:refresh:{해시}        → 발급 시점의 세대   (유효한 토큰)
    auth:refresh:used:{해시}   → 쓸 때의 세대       (이미 쓴 토큰의 흔적 — 재사용 감지용)
    auth:refresh:gen:{user_id} → 현재 세대          ("모든 세션 폐기"마다 하나씩 오른다. 만료가 없다)
    토큰 원문은 저장하지 않는다. 유저 ID 는 토큰 앞부분에서 읽는다.
    이 클래스는 decode_responses=True 인 클라이언트(core.redis.get_redis)를 전제로 한다.
    """

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def current_generation(self, user_id: int) -> int:
        return int(await self._redis.get(f"auth:refresh:gen:{user_id}") or 0)

    async def save(self, token: str, user_id: int, generation: int) -> None:
        await self._redis.set(f"auth:refresh:{_digest(token)}", generation, ex=self._ttl)

    async def take(self, token: str) -> RefreshLookup:
        user_id = refresh_token_user_id(token)
        if user_id is None:
            return RefreshLookup(RefreshStatus.MISSING, None)
        digest = _digest(token)
        result = await self._redis.eval(
            _TAKE_SCRIPT,
            3,
            f"auth:refresh:{digest}",
            f"auth:refresh:used:{digest}",
            f"auth:refresh:gen:{user_id}",
            self._ttl,
        )
        if result[0] == "active":
            return RefreshLookup(RefreshStatus.ACTIVE, user_id, int(result[1]))
        if result[0] == "used":
            return RefreshLookup(RefreshStatus.USED, user_id)
        return RefreshLookup(RefreshStatus.MISSING, None)

    async def revoke(self, token: str) -> None:
        await self._redis.delete(f"auth:refresh:{_digest(token)}")

    async def revoke_all(self, user_id: int) -> None:
        await self._redis.incr(f"auth:refresh:gen:{user_id}")
