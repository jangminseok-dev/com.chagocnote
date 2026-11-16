from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from guardian.adapter.outbound.mappers.guardian_mapper import to_link
from guardian.adapter.outbound.orm.guardian_orm import GuardianLinkOrm
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.entities.guardian_link import GuardianLink
from guardian.domain.errors import GuardianAlreadyLinkedError

_LIVE_INDEX = "uq_guardian_links_live"
_L = GuardianLinkOrm


class GuardianLinkPgRepository(GuardianLinkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _one(self, *conditions) -> GuardianLink | None:
        row = (
            await self._session.execute(
                select(_L).where(_L.ended_at.is_(None), *conditions).execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_link(row) if row is not None else None

    async def create(
        self, user_id: int, shop_id: int, customer_id: int, verified_by: str, now: datetime
    ) -> GuardianLink:
        statement = (
            insert(_L)
            .values(user_id=user_id, shop_id=shop_id, customer_id=customer_id, verified_by=verified_by,
                    created_at=now)
            .returning(_L)
            .execution_options(populate_existing=True)
        )
        # 세이브포인트 — 유일 위반이 트랜잭션 전체를 버리지 않게. 동시에 온 둘째는 첫째의 커밋까지 색인에서 기다렸다가 여기서 걸린다.
        try:
            async with self._session.begin_nested():
                row = (await self._session.execute(statement)).scalar_one()
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) == _LIVE_INDEX:
                raise GuardianAlreadyLinkedError("이미 다른 계정에 연결된 고객입니다.") from exc
            raise
        return to_link(row)

    async def find_live_for_customer(self, shop_id: int, customer_id: int) -> GuardianLink | None:
        """그 카드의 기본 연결(가족 연결은 빼고)."""
        return await self._one(_L.shop_id == shop_id, _L.customer_id == customer_id, _L.parent_link_id.is_(None))

    async def get_live(self, user_id: int, link_id: int) -> GuardianLink | None:
        return await self._one(_L.id == link_id, _L.user_id == user_id)

    async def list_live_for_user(self, user_id: int) -> list[GuardianLink]:
        rows = await self._session.execute(
            select(_L)
            .where(_L.user_id == user_id, _L.ended_at.is_(None))
            .order_by(_L.created_at, _L.id)
            .execution_options(populate_existing=True)
        )
        return [to_link(row) for row in rows.scalars()]

    async def _end(self, ended_by: str, now: datetime, *conditions) -> int:
        ended = await self._session.execute(
            update(_L).where(_L.ended_at.is_(None), *conditions).values(ended_at=now, ended_by=ended_by)
        )
        return ended.rowcount

    async def end(self, link_id: int, ended_by: str, now: datetime) -> bool:
        return await self._end(ended_by, now, _L.id == link_id) == 1

    async def end_all_for_user(self, user_id: int, now: datetime) -> int:
        return await self._end("withdrawn", now, _L.user_id == user_id)

    async def end_all_for_customer(self, shop_id: int, customer_id: int, now: datetime) -> int:
        return await self._end("anonymized", now, _L.shop_id == shop_id, _L.customer_id == customer_id)

    # --- 가족(⑫) ---

    async def lock_primary(self, link_id: int) -> GuardianLink | None:
        found = await self.lock_primaries([link_id])
        return found[0] if found else None

    async def lock_primaries(self, link_ids: list[int]) -> list[GuardianLink]:
        if not link_ids:
            return []
        rows = await self._session.execute(
            select(_L)
            .where(_L.id.in_(link_ids), _L.ended_at.is_(None), _L.parent_link_id.is_(None))
            .order_by(_L.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return [to_link(row) for row in rows.scalars()]

    async def primaries_reached_by(self, user_id: int) -> list[int]:
        rows = await self._session.execute(
            select(func.coalesce(_L.parent_link_id, _L.id)).where(_L.user_id == user_id, _L.ended_at.is_(None)))
        return sorted({row for row in rows.scalars()})

    async def create_family(self, user_id: int, primary: GuardianLink, now: datetime) -> GuardianLink:
        row = (
            await self._session.execute(
                insert(_L)
                .values(user_id=user_id, shop_id=primary.shop_id, customer_id=primary.customer_id,
                        verified_by="family_invite", parent_link_id=primary.id, created_at=now)
                .returning(_L)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_link(row)

    async def find_family(self, primary_id: int, user_id: int) -> GuardianLink | None:
        return await self._one(_L.parent_link_id == primary_id, _L.user_id == user_id)

    async def get_family(self, primary_id: int, family_id: int) -> GuardianLink | None:
        return await self._one(_L.parent_link_id == primary_id, _L.id == family_id)

    async def list_family(self, primary_id: int) -> list[GuardianLink]:
        rows = await self._session.execute(
            select(_L)
            .where(_L.parent_link_id == primary_id, _L.ended_at.is_(None))
            .order_by(_L.created_at, _L.id)
            .execution_options(populate_existing=True)
        )
        return [to_link(row) for row in rows.scalars()]

    async def family_counts(self, primary_ids: list[int]) -> dict[int, int]:
        if not primary_ids:
            return {}
        rows = await self._session.execute(
            select(_L.parent_link_id, func.count())
            .where(_L.parent_link_id.in_(primary_ids), _L.ended_at.is_(None))
            .group_by(_L.parent_link_id)
        )
        return {parent: count for parent, count in rows.all()}

    async def end_family(self, primary_ids: list[int], ended_by: str, now: datetime) -> int:
        if not primary_ids:
            return 0
        return await self._end(ended_by, now, _L.parent_link_id.in_(primary_ids))

    async def mark_family_seen(self, primary_id: int, now: datetime) -> None:
        await self._session.execute(
            update(_L)
            .where(_L.parent_link_id == primary_id, _L.ended_at.is_(None), _L.seen_by_primary_at.is_(None))
            .values(seen_by_primary_at=now)
        )

