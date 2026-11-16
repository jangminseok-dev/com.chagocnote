from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from guardian.adapter.outbound.orm.guardian_orm import GuardianShopSettingsOrm
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from guardian.domain.services.family_rules import FAMILY_MAX_DEFAULT

_S = GuardianShopSettingsOrm


class GuardianSettingsPgRepository(GuardianSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def family_max(self, shop_id: int) -> int:
        value = (await self._session.execute(select(_S.family_max).where(_S.shop_id == shop_id))).scalar_one_or_none()
        return FAMILY_MAX_DEFAULT if value is None else value

    async def put_family_max(self, shop_id: int, family_max: int) -> int:
        await self._session.execute(
            insert(_S).values(shop_id=shop_id, family_max=family_max)
            .on_conflict_do_update(index_elements=["shop_id"], set_={"family_max": family_max, "updated_at": func.now()})
        )
        return await self.family_max(shop_id)
