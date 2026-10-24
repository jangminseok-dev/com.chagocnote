"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeDirectory,
    FakeLedger,
    FakeMessages,
    FakeSettings,
    FakeShopProfile,
    FakeTemplates,
    SpyGateway,
)


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeChannels(), ChannelRepository)
    assert isinstance(FakeSettings(), SettingsRepository)
    assert isinstance(FakeTemplates(), TemplateRepository)
    messages = FakeMessages()
    assert isinstance(messages, MessageRepository) and isinstance(messages, NotificationQueueRepository)


def test_디스패처가_쓰는_허브_포트_스텁과_게이트웨이_스텁도_포트를_상속한다():
    assert isinstance(FakeShopProfile(), ShopProfilePort)
    assert isinstance(FakeDirectory(), CustomerDirectoryPort)
    assert isinstance(FakeLedger(), VisitLedgerPort)
    assert isinstance(SpyGateway(), MessageGatewayPort)
