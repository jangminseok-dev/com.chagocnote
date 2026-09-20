from __future__ import annotations

from redis.asyncio import Redis, from_url

from core.config import REDIS_URL

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = from_url(REDIS_URL, decode_responses=True)
    return _client


async def dispose_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None
