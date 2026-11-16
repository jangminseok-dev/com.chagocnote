"""guardian 의 저장소·제한기를 만드는 곳. 프로바이더들이 함께 쓴다."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from guardian.adapter.outbound.pg.family_invite_pg_repository import FamilyInvitePgRepository
from guardian.adapter.outbound.pg.guardian_link_pg_repository import GuardianLinkPgRepository
from guardian.adapter.outbound.pg.guardian_settings_pg_repository import GuardianSettingsPgRepository
from guardian.adapter.outbound.redis.claim_redis_limiter import ClaimRedisLimiter
from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_link_repository(session: AsyncSession) -> GuardianLinkRepository:
    return GuardianLinkPgRepository(session)


def build_claim_limiter() -> ClaimLimiterPort:
    return ClaimRedisLimiter(get_redis())


def build_family_limiter() -> ClaimLimiterPort:
    """가족 초대 만들기와 잇기(⑫) — 계정당 시간당 10회, 잇기와 다른 이름 공간."""
    return ClaimRedisLimiter(get_redis(), namespace="family")


def build_invite_repository(session: AsyncSession) -> FamilyInviteRepository:
    return FamilyInvitePgRepository(session)


def build_settings_repository(session: AsyncSession) -> GuardianSettingsRepository:
    return GuardianSettingsPgRepository(session)
