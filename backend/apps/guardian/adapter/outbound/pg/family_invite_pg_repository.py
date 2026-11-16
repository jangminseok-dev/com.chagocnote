from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from guardian.adapter.outbound.mappers.guardian_mapper import to_invite
from guardian.adapter.outbound.orm.guardian_orm import GuardianFamilyInviteOrm
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.domain.entities.family_invite import FamilyInvite

_I = GuardianFamilyInviteOrm


class FamilyInvitePgRepository(FamilyInviteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, link_id: int, code_hash: str, now: datetime, expires_at: datetime) -> FamilyInvite:
        row = (
            await self._session.execute(
                insert(_I).values(link_id=link_id, code_hash=code_hash, created_at=now, expires_at=expires_at)
                .returning(_I).execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_invite(row)

    async def find(self, code_hash: str) -> FamilyInvite | None:
        row = (await self._session.execute(select(_I).where(_I.code_hash == code_hash))).scalar_one_or_none()
        return to_invite(row) if row is not None else None

    async def lock(self, invite_id: int) -> FamilyInvite | None:
        row = (
            await self._session.execute(
                select(_I).where(_I.id == invite_id).with_for_update().execution_options(populate_existing=True))
        ).scalar_one_or_none()
        return to_invite(row) if row is not None else None

    async def revoke_unused(self, link_ids: list[int], now: datetime) -> int:
        if not link_ids:
            return 0
        done = await self._session.execute(
            update(_I).where(_I.link_id.in_(link_ids), _I.used_at.is_(None), _I.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return done.rowcount

    async def mark_used(self, invite_id: int, now: datetime) -> None:
        await self._session.execute(update(_I).where(_I.id == invite_id).values(used_at=now))
