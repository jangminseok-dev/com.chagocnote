"""연동 — token_requested 에서만, 틀린 토큰 400, 성공하면 linked·설정 기본값·기본 5종 템플릿 등록(하나 실패해도 계속)."""
import logging

import pytest

from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.ports.output.message_gateway_port import GatewayPermanentError, GatewayTransientError
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.channel_status import LINKED, TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, DEFAULT_KINDS, REMINDER, REPORT
from notification.domain.value_objects.template_status import PENDING
from notification.tests.helpers.builders import channel, ctx, kst
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld

COMMAND = LinkChannelCommand(ctx=ctx(), search_id="hisshaus", admin_phone="01012345678", category_code="003001",
                             token="000000")


def _requested() -> OnboardingWorld:
    world = OnboardingWorld(linked=False)
    world.channels.rows[1] = channel(status=TOKEN_REQUESTED, provider_channel_id=None, linked_at=None)
    return world


async def test_맞는_토큰이면_linked_가_되고_설정_기본값과_기본_5종_템플릿이_pending_으로_생긴다():
    world = _requested()
    view = await world.link.link_channel(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.status, saved.provider_channel_id, saved.linked_at) == (LINKED, "pf-hisshaus", NOW)
    assert world.settings.rows[1].reminder_time.strftime("%H:%M") == "18:00"
    assert world.template_ids() == [(kind, PENDING) for kind in DEFAULT_KINDS]
    assert world.templates.rows[(1, CONFIRM)].provider_template_id == f"tpl-pf-hisshaus-{CONFIRM}-v{TEXT_VERSION}"
    assert world.templates.rows[(1, CONFIRM)].text_version == TEXT_VERSION
    assert all(t.requested_at == NOW for t in world.templates.rows.values())
    assert (view.channel.status, view.settings is not None, [t.kind for t in view.templates]) == (
        LINKED, True, list(DEFAULT_KINDS))
    assert ("link_channel", "hisshaus", "01012345678", "003001") in world.gateway.calls
    assert world.limiter.calls == [(1, "link")]


async def test_업체_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다():
    world = _requested()
    await world.link.link_channel(COMMAND)
    names = [entry[0] for entry in world.journal]
    assert names.index("register_template") < names.index("save_channel")
    assert names.index("save_channel") < names.index("ensure_settings") < names.index("upsert_template")


async def test_틀린_토큰이면_400_이고_채널은_token_requested_그대로다():
    world = _requested()
    with pytest.raises(TokenInvalidError):
        await world.link.link_channel(LinkChannelCommand(**{**COMMAND.__dict__, "token": "123456"}))
    assert world.channels.rows[1].status == TOKEN_REQUESTED
    assert world.template_ids() == [] and 1 not in world.settings.rows
    assert world.limiter.calls == [(1, "link")]


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = _requested()
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.link.link_channel(COMMAND)
    assert world.gateway.calls == []


@pytest.mark.parametrize("status", [None, UNLINKED])
async def test_토큰을_받지_않은_매장은_409_NOT_LINKED_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status, provider_channel_id=None, linked_at=None)
    with pytest.raises(ChannelNotLinkedError):
        await world.link.link_channel(COMMAND)
    assert world.gateway.calls == []


async def test_이미_연동된_매장은_409_LINKED_다():
    world = OnboardingWorld()
    with pytest.raises(ChannelAlreadyLinkedError):
        await world.link.link_channel(COMMAND)
    assert world.gateway.calls == []


async def test_연동_호출의_업체_오류는_502_다():
    world = _requested()

    async def failing(*args):
        raise GatewayTransientError("timeout")

    world.gateway.link_channel = failing
    with pytest.raises(ProviderUnavailableError):
        await world.link.link_channel(COMMAND)
    assert world.channels.rows[1].status == TOKEN_REQUESTED


async def test_템플릿_등록_하나가_실패하면_그_종류만_빼고_넷을_등록하고_경고만_남긴다(caplog):
    world = _requested()
    original = world.gateway.register_template

    async def flaky(provider_channel_id, template, text_version):
        if template.kind == REPORT:
            raise GatewayPermanentError("400")
        return await original(provider_channel_id, template, text_version)

    world.gateway.register_template = flaky
    with caplog.at_level(logging.WARNING):
        view = await world.link.link_channel(COMMAND)
    assert world.channels.rows[1].status == LINKED
    assert world.template_ids() == [(k, PENDING) for k in (CONFIRM, REMINDER, CHANGE, CANCEL)]
    assert [t.kind for t in view.templates] == [CONFIRM, REMINDER, CHANGE, CANCEL]
    assert [r.levelname for r in caplog.records] == ["WARNING"] and REPORT in caplog.text
