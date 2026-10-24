"""토큰 신청 — 연동된 매장은 409, 횟수 제한 429, 업체 오류 502, 성공하면 채널 줄을 token_requested 로 upsert."""
import pytest

from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand
from notification.app.ports.output.message_gateway_port import GatewayPermanentError, GatewayTransientError
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED, UNLINKED
from notification.tests.helpers.builders import channel, ctx, kst
from notification.tests.helpers.onboarding_world import OnboardingWorld

COMMAND = RequestChannelTokenCommand(ctx=ctx(), search_id="hisshaus", admin_phone="01012345678",
                                     category_code="003001")


async def test_처음_신청하면_채널_줄이_token_requested_로_생기고_업체에_토큰을_신청한다():
    world = OnboardingWorld(linked=False)
    await world.token.request_channel_token(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.shop_id, saved.status, saved.provider, saved.provider_channel_id, saved.linked_at) == (
        1, TOKEN_REQUESTED, "solapi", None, None)
    assert saved.sms_fallback_enabled is False and saved.sender_number is None
    assert world.gateway.calls == [("request_channel_token", "hisshaus", "01012345678", "003001")]
    assert world.limiter.calls == [(1, "token")]


async def test_해제된_매장이_다시_신청하면_되살린다_발신번호와_문자_대체는_남는다():
    world = OnboardingWorld(linked=False)
    world.channels.rows[1] = channel(status=UNLINKED, provider_channel_id=None, linked_at=None,
                                     unlinked_at=kst(10, 10, 9), sender_number="0212345678",
                                     sender_number_verified_at=kst(10, 5, 9), sms_fallback_enabled=True)
    await world.token.request_channel_token(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.status, saved.provider_channel_id, saved.linked_at) == (TOKEN_REQUESTED, None, None)
    assert (saved.sender_number, saved.sender_number_verified_at, saved.sms_fallback_enabled) == (
        "0212345678", kst(10, 5, 9), True)


async def test_연동된_매장이_다시_신청하면_409_이고_업체를_부르지_않는다():
    world = OnboardingWorld()
    with pytest.raises(ChannelAlreadyLinkedError):
        await world.token.request_channel_token(COMMAND)
    assert world.gateway.calls == [] and world.limiter.calls == []
    assert world.channels.rows[1].status == "linked"


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = OnboardingWorld(linked=False)
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.token.request_channel_token(COMMAND)
    assert world.gateway.calls == [] and 1 not in world.channels.rows


@pytest.mark.parametrize("error", [GatewayTransientError("timeout"), GatewayPermanentError("401")])
async def test_업체_오류는_502_이고_채널_줄을_만들지_않는다(error):
    world = OnboardingWorld(linked=False)

    async def failing(*args):
        raise error

    world.gateway.request_channel_token = failing
    with pytest.raises(ProviderUnavailableError):
        await world.token.request_channel_token(COMMAND)
    assert 1 not in world.channels.rows


async def test_관리자_번호와_검색_아이디는_저장하지_않는다():
    world = OnboardingWorld(linked=False)
    await world.token.request_channel_token(COMMAND)
    assert "01012345678" not in repr(world.channels.rows[1]) and "hisshaus" not in repr(world.channels.rows[1])
