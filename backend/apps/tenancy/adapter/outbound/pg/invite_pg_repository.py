from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.mappers.tenancy_mapper import to_invite
from tenancy.adapter.outbound.orm.tenancy_orm import RoleOrm, ShopInviteOrm
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.domain.entities.invite import Invite
from tenancy.domain.value_objects.role_code import RoleCode


class InvitePgRepository(InviteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, ctx: ShopContext, role: RoleCode, code_hash: str, expires_at: datetime, max_uses: int
    ) -> Invite:
        return await self._insert(ctx.shop_id, role, code_hash, ctx.member_id, expires_at, max_uses)

    async def create_owner_invite(self, shop_id: int, code_hash: str, expires_at: datetime) -> Invite:
        return await self._insert(shop_id, RoleCode.OWNER, code_hash, None, expires_at, 1)

    async def find_by_code_hash_for_update(self, code_hash: str) -> Invite | None:
        stmt = (
            select(ShopInviteOrm, RoleOrm.code)
            .join(RoleOrm, RoleOrm.id == ShopInviteOrm.role_id)
            .where(ShopInviteOrm.code_hash == code_hash)
            .with_for_update(of=ShopInviteOrm)
        )
        row = (await self._session.execute(stmt)).first()
        return to_invite(row[0], row[1]) if row else None

    async def mark_used(self, invite_id: int) -> None:
        await self._session.execute(
            update(ShopInviteOrm)
            .where(ShopInviteOrm.id == invite_id)
            .values(used_count=ShopInviteOrm.used_count + 1)
        )

    async def revoke_created_by(self, ctx: ShopContext, member_id: int) -> None:
        await self._session.execute(
            update(ShopInviteOrm)
            .where(
                ShopInviteOrm.shop_id == ctx.shop_id,
                ShopInviteOrm.created_by_member_id == member_id,
                ShopInviteOrm.revoked_at.is_(None),
                ShopInviteOrm.used_count < ShopInviteOrm.max_uses,
            )
            .values(revoked_at=func.now())
        )

    async def _insert(
        self, shop_id: int, role: RoleCode, code_hash: str,
        created_by_member_id: int | None, expires_at: datetime, max_uses: int,
    ) -> Invite:
        role_id = (
            await self._session.execute(select(RoleOrm.id).where(RoleOrm.code == role.value))
        ).scalar_one()
        row = ShopInviteOrm(
            shop_id=shop_id, role_id=role_id, code_hash=code_hash,
            created_by_member_id=created_by_member_id, expires_at=expires_at,
            max_uses=max_uses, used_count=0,
        )
        self._session.add(row)
        await self._session.flush()
        return to_invite(row, role.value)
