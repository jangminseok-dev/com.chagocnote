"""발신번호 인증 시작 — linked 필요, 횟수 제한, 업체 오류 502. 아무것도 저장하지 않는다."""
import pytest

from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED
from notification.tests.helpers.builders import channel, ctx
from notification.tests.helpers.onboarding_world import OnboardingWorld

COMMAND = RequestSenderVerificationCommand(ctx=ctx(), phone="0212345678")


async def test_업체에_인증을_요청하고_저장은_하지_않는다():
    world = OnboardingWorld()
    before = world.channels.rows[1]
    await world.sender_verification.request_sender_verification(COMMAND)
    assert world.gateway.calls == [("request_sender_verification", "0212345678")]
    assert world.channels.rows[1] == before and ("save_channel", 1, "linked") not in world.journal
    assert world.limiter.calls == [(1, "sender_verification")]


@pytest.mark.parametrize("status", [None, TOKEN_REQUESTED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.sender_verification.request_sender_verification(COMMAND)
    assert world.gateway.calls == []


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = OnboardingWorld()
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.sender_verification.request_sender_verification(COMMAND)
    assert world.gateway.calls == []


async def test_업체_오류는_502_다():
    world = OnboardingWorld()

    async def failing(phone):
        raise GatewayTransientError("timeout")

    world.gateway.request_sender_verification = failing
    with pytest.raises(ProviderUnavailableError):
        await world.sender_verification.request_sender_verification(COMMAND)
