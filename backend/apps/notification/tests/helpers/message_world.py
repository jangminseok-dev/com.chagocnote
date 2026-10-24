"""발송 내역·다시 보내기·단건 조회 인터랙터 테스트의 세계 — 연동된 매장 1(채널 linked·설정 기본값·템플릿 6종 approved)과
고객 1·반려동물 101. wake 는 journal 에 ("wake",) 로 남는다."""
from __future__ import annotations

from hub.app.dtos.shop_profile import ShopProfile
from notification.app.use_cases.get_notification_message_interactor import GetNotificationMessageInteractor
from notification.app.use_cases.list_visit_notifications_interactor import ListVisitNotificationsInteractor
from notification.app.use_cases.resend_notification_interactor import ResendNotificationInteractor
from notification.domain.value_objects.message_kind import KINDS
from notification.tests.helpers.builders import TZ, channel, kst, settings, template
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeDirectory,
    FakeMessages,
    FakeSettings,
    FakeShopProfile,
    FakeTemplates,
    Journal,
)

NOW = kst(10, 14, 11)
SHOP_NAME = "두부네"


class MessageWorld:
    def __init__(self, *, now=NOW) -> None:
        self.journal = Journal()
        self.channels = FakeChannels(self.journal)
        self.settings = FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.shops = FakeShopProfile({1: ShopProfile(shop_id=1, name=SHOP_NAME, phone=None, address=None,
                                                     timezone=TZ, open=True)})
        self.directory = FakeDirectory()
        self.directory.family()
        self.now = now
        self.channels.rows[1] = channel()
        self.settings.rows[1] = settings()
        for i, kind in enumerate(KINDS, start=1):
            self.templates.rows[(1, kind)] = template(id=i, kind=kind, provider_template_id=f"KA01TP000{i}")

    def wake(self) -> None:
        self.journal.append(("wake",))

    @property
    def list(self) -> ListVisitNotificationsInteractor:
        return ListVisitNotificationsInteractor(messages=self.messages, shops=self.shops, directory=self.directory)

    @property
    def get(self) -> GetNotificationMessageInteractor:
        return GetNotificationMessageInteractor(messages=self.messages, shops=self.shops, directory=self.directory)

    @property
    def resend(self) -> ResendNotificationInteractor:
        return ResendNotificationInteractor(
            channels=self.channels, templates=self.templates, messages=self.messages, now=lambda: self.now,
            wake=self.wake)
