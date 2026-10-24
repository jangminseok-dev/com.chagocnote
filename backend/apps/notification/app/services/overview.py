"""한눈에 보기 읽기 — 조회와 연동·설정·발신번호 확인 명령이 같은 모양을 돌려준다."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository


async def load_overview(
    ctx: ShopContext, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
) -> NotificationOverviewView:
    return NotificationOverviewView(
        channel=await channels.get(ctx), settings=await settings.get(ctx), templates=await templates.list_for_shop(ctx),
    )
