"""tenancy 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.adapter.outbound.redis.invite_attempt_redis_limiter import InviteAttemptRedisLimiter
from tenancy.app.ports.output.invite_attempt_limiter_port import InviteAttemptLimiterPort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.app.ports.output.shop_repository import ShopRepository


def build_shop_repository(db: AsyncSession) -> ShopRepository:
    return ShopPgRepository(db)


def build_member_repository(db: AsyncSession) -> MemberRepository:
    return MemberPgRepository(db)


def build_invite_repository(db: AsyncSession) -> InviteRepository:
    return InvitePgRepository(db)


def build_invite_attempt_limiter() -> InviteAttemptLimiterPort:
    return InviteAttemptRedisLimiter(get_redis())
