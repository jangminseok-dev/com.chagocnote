"""notification 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository


def build_channel_repository(db: AsyncSession) -> ChannelRepository:
    return ChannelPgRepository(db)


def build_settings_repository(db: AsyncSession) -> SettingsRepository:
    return SettingsPgRepository(db)


def build_template_repository(db: AsyncSession) -> TemplateRepository:
    return TemplatePgRepository(db)


def build_message_repository(db: AsyncSession) -> MessagePgRepository:
    """notification_messages 표의 리포지토리 하나. 매장 범위 포트와 디스패처의 전 매장 포트를 다 구현한다."""
    return MessagePgRepository(db)
