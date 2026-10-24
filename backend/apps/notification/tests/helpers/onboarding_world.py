"""온보딩·설정 인터랙터 테스트의 세계 — 스텁 저장소·SpyGateway·스텁 제한기로 인터랙터 일곱을 만든다."""
from __future__ import annotations

from notification.app.use_cases.confirm_sender_interactor import ConfirmSenderInteractor
from notification.app.use_cases.get_notification_overview_interactor import GetNotificationOverviewInteractor
from notification.app.use_cases.link_channel_interactor import LinkChannelInteractor
from notification.app.use_cases.request_channel_token_interactor import RequestChannelTokenInteractor
from notification.app.use_cases.request_sender_verification_interactor import (
    RequestSenderVerificationInteractor,
)
from notification.app.use_cases.unlink_channel_interactor import UnlinkChannelInteractor
from notification.app.use_cases.update_notification_settings_interactor import (
    UpdateNotificationSettingsInteractor,
)
from notification.domain.value_objects.message_kind import DEFAULT_KINDS
from notification.tests.helpers.builders import channel, kst, settings, template
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeMessages,
    FakeOnboardingLimiter,
    FakeSettings,
    FakeTemplates,
    Journal,
    SpyGateway,
)

NOW = kst(10, 14, 11)


class OnboardingWorld:
    """linked=True 면 매장 1 이 연동되어 있고(채널 linked·설정 기본값·기본 5종 approved), False 면 채널이 없다."""

    def __init__(self, *, linked: bool = True, now=NOW) -> None:
        self.journal = Journal()
        self.channels = FakeChannels(self.journal)
        self.settings = FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.gateway = SpyGateway(self.journal)
        self.limiter = FakeOnboardingLimiter()
        self.now = now
        if linked:
            self.channels.rows[1] = channel()
            self.settings.rows[1] = settings()
            for i, kind in enumerate(DEFAULT_KINDS, start=1):
                self.templates.rows[(1, kind)] = template(id=i, kind=kind, provider_template_id=f"KA01TP000{i}")

    @property
    def overview(self) -> GetNotificationOverviewInteractor:
        return GetNotificationOverviewInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates)

    @property
    def token(self) -> RequestChannelTokenInteractor:
        return RequestChannelTokenInteractor(channels=self.channels, gateway=self.gateway, limiter=self.limiter)

    @property
    def link(self) -> LinkChannelInteractor:
        return LinkChannelInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, gateway=self.gateway,
            limiter=self.limiter, now=lambda: self.now)

    @property
    def unlink(self) -> UnlinkChannelInteractor:
        return UnlinkChannelInteractor(
            channels=self.channels, templates=self.templates, messages=self.messages, now=lambda: self.now)

    @property
    def update_settings(self) -> UpdateNotificationSettingsInteractor:
        return UpdateNotificationSettingsInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, messages=self.messages,
            gateway=self.gateway, now=lambda: self.now)

    @property
    def sender_verification(self) -> RequestSenderVerificationInteractor:
        return RequestSenderVerificationInteractor(channels=self.channels, gateway=self.gateway, limiter=self.limiter)

    @property
    def confirm_sender(self) -> ConfirmSenderInteractor:
        return ConfirmSenderInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, gateway=self.gateway,
            limiter=self.limiter, now=lambda: self.now)

    def template_ids(self) -> list[tuple[str, str]]:
        return [(t.kind, t.status) for t in sorted(self.templates.rows.values(), key=lambda t: t.id)
                if t.shop_id == 1]
