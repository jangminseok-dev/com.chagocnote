"""notification 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import APP_ENV, SOLAPI_API_KEY, SOLAPI_API_SECRET
from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
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


def build_message_gateway(api_key: str, api_secret: str, app_env: str) -> MessageGatewayPort:
    """키가 둘 다 있으면 솔라피, 둘 다 비고 dev 면 가짜. 그 밖(하나만 있거나 운영에서 빔)은 기동 실패(설계 6.1)."""
    if api_key and api_secret:
        return SolapiGateway(api_key, api_secret)
    if not api_key and not api_secret and app_env == "dev":
        return FakeGateway()
    raise RuntimeError("SOLAPI_API_KEY 와 SOLAPI_API_SECRET 을 둘 다 넣거나(운영) 둘 다 비워야(dev) 합니다.")


_gateway: MessageGatewayPort | None = None


def get_message_gateway() -> MessageGatewayPort:
    """프로세스에 하나 — HTTP 클라이언트를 나눠 쓴다. 테스트는 monkeypatch 로 바꾼다."""
    global _gateway
    if _gateway is None:
        _gateway = build_message_gateway(SOLAPI_API_KEY, SOLAPI_API_SECRET, APP_ENV)
    return _gateway


def reset_message_gateway() -> None:
    """테스트용."""
    global _gateway
    _gateway = None
