from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.customer_orm import PetConditionTypeOrm
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.domain.entities.condition_type import ConditionType


class ConditionTypePgRepository(ConditionTypeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ConditionType]:
        rows = (
            await self._session.execute(
                select(PetConditionTypeOrm).order_by(PetConditionTypeOrm.sort_order)
            )
        ).scalars()
        return [ConditionType(code=r.code, label=r.label, sort_order=r.sort_order) for r in rows]
