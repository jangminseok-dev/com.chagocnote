from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.orm.operator_orm import PlatformOperatorOrm
from auth.app.ports.output.operator_repository import OperatorRepository


class OperatorPgRepository(OperatorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_operator(self, user_id: int) -> bool:
        stmt = select(PlatformOperatorOrm.id).where(PlatformOperatorOrm.user_id == user_id)
        return (await self._session.execute(stmt)).first() is not None

    async def grant(self, user_id: int) -> None:
        await self._session.execute(
            insert(PlatformOperatorOrm)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )

    async def revoke(self, user_id: int) -> None:
        await self._session.execute(
            delete(PlatformOperatorOrm).where(PlatformOperatorOrm.user_id == user_id)
        )
