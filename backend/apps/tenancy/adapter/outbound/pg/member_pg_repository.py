from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.membership_summary import MembershipSummary
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.mappers.tenancy_mapper import to_member
from tenancy.adapter.outbound.orm.tenancy_orm import (
    PermissionOrm,
    RoleOrm,
    RolePermissionOrm,
    ShopMemberOrm,
    ShopOrm,
)
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import AlreadyMemberError
from tenancy.domain.value_objects.role_code import RoleCode


class MemberPgRepository(MemberRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_membership_changes(self, shop_id: int) -> None:
        await self._session.execute(
            select(ShopOrm.id).where(ShopOrm.id == shop_id).with_for_update()
        )

    async def find_access(self, shop_id: int, user_id: int) -> ShopAccessRecord | None:
        stmt = (
            select(
                ShopMemberOrm.id, RoleOrm.id, RoleOrm.code, ShopOrm.suspended_at, ShopOrm.closed_at
            )
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .join(ShopOrm, ShopOrm.id == ShopMemberOrm.shop_id)
            .where(
                ShopMemberOrm.shop_id == shop_id,
                ShopMemberOrm.user_id == user_id,
                ShopMemberOrm.removed_at.is_(None),
            )
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        member_id, role_id, role_code, suspended_at, closed_at = row
        codes = (
            await self._session.execute(
                select(PermissionOrm.code)
                .join(RolePermissionOrm, RolePermissionOrm.permission_id == PermissionOrm.id)
                .where(RolePermissionOrm.role_id == role_id)
            )
        ).scalars()
        return ShopAccessRecord(
            member_id=member_id,
            role=role_code,
            permissions=frozenset(codes),
            shop_suspended=suspended_at is not None,
            shop_closed=closed_at is not None,
        )

    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        stmt = (
            select(ShopOrm.id, ShopOrm.name, RoleOrm.code)
            .select_from(ShopMemberOrm)
            .join(ShopOrm, ShopOrm.id == ShopMemberOrm.shop_id)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(
                ShopMemberOrm.user_id == user_id,
                ShopMemberOrm.removed_at.is_(None),
                ShopOrm.closed_at.is_(None),
            )
            .order_by(ShopOrm.id)
        )
        return [
            MembershipSummary(shop_id=shop_id, shop_name=name, role=role)
            for shop_id, name, role in (await self._session.execute(stmt)).all()
        ]

    async def add(self, shop_id: int, user_id: int, role: RoleCode) -> Member:
        row = ShopMemberOrm(shop_id=shop_id, user_id=user_id, role_id=await self._role_id(role))
        try:
            # 세이브포인트 안에서 넣는다. 유일 제약에 걸려도 바깥 트랜잭션은 계속 쓸 수 있다.
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError as exc:
            # 지금 속해 있는 행의 유일 제약일 때만 도메인 오류로 바꾼다. 나머지는 그대로 올린다.
            # asyncpg 는 제약 이름을 원인 예외에 담고, SQLAlchemy 는 그것을 __cause__ 로 감싼다.
            if getattr(exc.orig.__cause__, "constraint_name", None) != "uq_shop_members_active":
                raise
            raise AlreadyMemberError("이미 이 매장의 멤버입니다.") from exc
        await self._session.refresh(row)  # 서버 기본값 joined_at 을 읽어 온다
        return to_member(row, role.value)

    async def list_active(self, ctx: ShopContext) -> list[Member]:
        stmt = self._active(ctx).order_by(ShopMemberOrm.id)
        return [to_member(m, code) for m, code in (await self._session.execute(stmt)).all()]

    async def get_active(self, ctx: ShopContext, member_id: int) -> Member | None:
        row = (
            await self._session.execute(self._active(ctx).where(ShopMemberOrm.id == member_id))
        ).first()
        return to_member(row[0], row[1]) if row else None

    async def count_owners(self, ctx: ShopContext) -> int:
        stmt = (
            select(ShopMemberOrm.id)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(
                ShopMemberOrm.shop_id == ctx.shop_id,
                ShopMemberOrm.removed_at.is_(None),
                RoleOrm.code == RoleCode.OWNER.value,
            )
            .with_for_update(of=ShopMemberOrm)
        )
        return len((await self._session.execute(stmt)).scalars().all())

    async def change_role(self, ctx: ShopContext, member_id: int, role: RoleCode) -> None:
        await self._session.execute(
            self._update_active(ctx, member_id).values(role_id=await self._role_id(role))
        )

    async def remove(self, ctx: ShopContext, member_id: int) -> None:
        await self._session.execute(
            self._update_active(ctx, member_id).values(removed_at=func.now())
        )

    def _active(self, ctx: ShopContext):
        return (
            select(ShopMemberOrm, RoleOrm.code)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(ShopMemberOrm.shop_id == ctx.shop_id, ShopMemberOrm.removed_at.is_(None))
        )

    def _update_active(self, ctx: ShopContext, member_id: int):
        return update(ShopMemberOrm).where(
            ShopMemberOrm.id == member_id,
            ShopMemberOrm.shop_id == ctx.shop_id,
            ShopMemberOrm.removed_at.is_(None),
        )

    async def _role_id(self, role: RoleCode) -> int:
        return (
            await self._session.execute(select(RoleOrm.id).where(RoleOrm.code == role.value))
        ).scalar_one()
