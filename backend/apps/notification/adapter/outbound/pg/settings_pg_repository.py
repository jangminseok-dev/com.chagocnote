from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import settings_values, to_settings
from notification.adapter.outbound.orm.notification_orm import NotificationSettingsOrm
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS, NotificationSettings


class SettingsPgRepository(SettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> NotificationSettings | None:
        row = (
            await self._session.execute(
                select(NotificationSettingsOrm)
                .where(NotificationSettingsOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_settings(row) if row is not None else None

    async def ensure(self, ctx: ShopContext) -> NotificationSettings:
        # 동시에 처음 쓰는 두 요청 중 늦은 쪽은 앞선 쪽의 커밋까지 기다렸다가 DO NOTHING 이 된다.
        await self._session.execute(
            pg_insert(NotificationSettingsOrm)
            .values(shop_id=ctx.shop_id, **settings_values(DEFAULT_NOTIFICATION_SETTINGS))
            .on_conflict_do_nothing(index_elements=[NotificationSettingsOrm.shop_id])
        )
        return await self.get(ctx)

    async def update(self, ctx: ShopContext, settings: NotificationSettings) -> NotificationSettings:
        row = (
            await self._session.execute(
                update(NotificationSettingsOrm)
                .where(NotificationSettingsOrm.shop_id == ctx.shop_id)
                .values(**settings_values(settings))
                .returning(NotificationSettingsOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_settings(row)
