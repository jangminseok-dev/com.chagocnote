"""발신번호 확인 — 맞으면 번호와 인증 시각을 적고 overview, 틀리면 400, 횟수 제한 429."""
import pytest

from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import UNLINKED
from notification.tests.helpers.builders import channel, ctx
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld

COMMAND = ConfirmSenderCommand(ctx=ctx(), phone="0212345678", code="000000")


async def test_맞는_인증번호면_발신번호와_인증_시각을_적고_overview_를_돌려준다():
    world = OnboardingWorld()
    view = await world.confirm_sender.confirm_sender(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.sender_number, saved.sender_number_verified_at, saved.status) == ("0212345678", NOW, "linked")
    assert (view.channel.sender_number, view.settings is not None, len(view.templates)) == ("0212345678", True, 5)
    assert world.gateway.calls == [("confirm_sender_verification", "0212345678")]
    assert world.limiter.calls == [(1, "sender_confirm")]


async def test_틀린_인증번호면_400_이고_아무것도_적지_않는다():
    world = OnboardingWorld()
    with pytest.raises(TokenInvalidError):
        await world.confirm_sender.confirm_sender(ConfirmSenderCommand(ctx=ctx(), phone="0212345678", code="111111"))
    assert world.channels.rows[1].sender_number is None and world.limiter.calls == [(1, "sender_confirm")]


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = OnboardingWorld()
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.confirm_sender.confirm_sender(COMMAND)
    assert world.gateway.calls == []


@pytest.mark.parametrize("status", [None, UNLINKED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.confirm_sender.confirm_sender(COMMAND)


async def test_업체_오류는_502_다():
    world = OnboardingWorld()

    async def failing(phone, code):
        raise GatewayTransientError("timeout")

    world.gateway.confirm_sender_verification = failing
    with pytest.raises(ProviderUnavailableError):
        await world.confirm_sender.confirm_sender(COMMAND)
    assert world.channels.rows[1].sender_number is None
