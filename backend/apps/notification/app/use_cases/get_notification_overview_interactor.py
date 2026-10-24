from __future__ import annotations

from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.input.get_notification_overview_use_case import GetNotificationOverviewUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview


class GetNotificationOverviewInteractor(GetNotificationOverviewUseCase):
    """읽기만 한다 — 연동 전 매장은 채널 None·설정 None·템플릿 빈 목록이고 아무 줄도 만들지 않는다."""

    def __init__(self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates

    async def get_notification_overview(self, query: GetNotificationOverviewQuery) -> NotificationOverviewView:
        return await load_overview(query.ctx, self._channels, self._settings, self._templates)
