from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import channel_values, to_channel
from notification.adapter.outbound.orm.notification_orm import NotificationChannelOrm
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.domain.entities.notification_channel import NotificationChannel


class ChannelPgRepository(ChannelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> NotificationChannel | None:
        row = (
            await self._session.execute(
                select(NotificationChannelOrm)
                .where(NotificationChannelOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_channel(row) if row is not None else None

    async def save(self, ctx: ShopContext, channel: NotificationChannel) -> NotificationChannel:
        if channel.shop_id != ctx.shop_id:
            raise ValueError("채널의 매장이 컨텍스트의 매장과 다릅니다.")
        values = channel_values(channel)
        row = (
            await self._session.execute(
                pg_insert(NotificationChannelOrm)
                .values(shop_id=ctx.shop_id, **values)
                .on_conflict_do_update(index_elements=[NotificationChannelOrm.shop_id], set_=values)
                .returning(NotificationChannelOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_channel(row)
