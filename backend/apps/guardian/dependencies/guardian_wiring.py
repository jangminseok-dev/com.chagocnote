"""guardian 의 저장소·제한기를 만드는 곳. 프로바이더들이 함께 쓴다."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from guardian.adapter.outbound.pg.guardian_link_pg_repository import GuardianLinkPgRepository
from guardian.adapter.outbound.redis.claim_redis_limiter import ClaimRedisLimiter
from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_link_repository(session: AsyncSession) -> GuardianLinkRepository:
    return GuardianLinkPgRepository(session)


def build_claim_limiter() -> ClaimLimiterPort:
    return ClaimRedisLimiter(get_redis())
