"""dev·흐름 테스트용 가짜 게이트웨이 — 번호 끝 네 자리와 토큰 000000 규칙이 결정적인지 본다."""
from __future__ import annotations

import pytest

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.ports.output.message_gateway_port import FallbackText, MessageGatewayPort, OutgoingMessage
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import TEMPLATES
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT


def _message(to: str, fallback: FallbackText | None = None) -> OutgoingMessage:
    return OutgoingMessage(to=to, provider_channel_id="pf-@dubu", provider_template_id="tpl-1",
                           variables={"매장명": "두부네"}, button_url=None, fallback=fallback)


def test_가짜_게이트웨이는_포트를_구현한다():
    assert isinstance(FakeGateway(), MessageGatewayPort)


async def test_토큰_000000_만_연동되고_채널_ID_는_검색_아이디에서_나온다():
    gateway = FakeGateway()
    await gateway.request_channel_token("@dubu", "01055550000", "001")
    assert await gateway.link_channel("@dubu", "01055550000", "001", "000000") == "pf-@dubu"
    with pytest.raises(TokenInvalidError):
        await gateway.link_channel("@dubu", "01055550000", "001", "123456")


async def test_템플릿은_즉시_승인되고_ID_에_채널_종류_판이_든다():
    gateway = FakeGateway()
    template_id = await gateway.register_template("pf-@dubu", TEMPLATES[CONFIRM], 2)
    assert template_id == "tpl-pf-@dubu-confirm-v2"
    state = await gateway.template_state(template_id)
    assert (state.status, state.rejected_reason) == ("approved", None)


async def test_반려_옵션을_켜면_다음_예약_제안_템플릿만_반려된다():
    gateway = FakeGateway(reject_next_visit=True)
    rejected = await gateway.template_state(await gateway.register_template("pf-1", TEMPLATES[NEXT_VISIT], 1))
    approved = await gateway.template_state(await gateway.register_template("pf-1", TEMPLATES[CONFIRM], 1))
    assert (rejected.status, rejected.rejected_reason) == ("rejected", "가짜 반려")
    assert approved.status == "approved"


async def test_발신번호_인증은_000000_만_통과한다():
    gateway = FakeGateway()
    await gateway.request_sender_verification("0215550000")
    await gateway.confirm_sender_verification("0215550000", "000000")
    with pytest.raises(TokenInvalidError):
        await gateway.confirm_sender_verification("0215550000", "123456")


async def test_발송은_늘_접수되고_호출_순서로_ID_가_붙는다():
    gateway = FakeGateway()
    first = await gateway.send(_message("01055551234"))
    second = await gateway.send(_message("01055550000"))
    assert (first.provider_message_id, second.provider_message_id) == ("fake-1", "fake-2")
    assert [m.to for m in gateway.sent_messages] == ["01055551234", "01055550000"]


async def test_번호_끝_네_자리로_결과를_가른다():
    gateway = FakeGateway()
    plain = await gateway.send(_message("01055551234"))
    permanent = await gateway.send(_message("01055550000"))
    transient = await gateway.send(_message("01055559999"))
    sent = await gateway.delivery_state(plain.provider_message_id)
    assert (sent.status, sent.channel_used, sent.error_code, sent.error_kind) == ("sent", "alimtalk", None, None)
    failed = await gateway.delivery_state(permanent.provider_message_id)
    assert (failed.status, failed.error_code, failed.error_kind) == ("failed", "3104", "permanent")
    retry = await gateway.delivery_state(transient.provider_message_id)
    assert (retry.status, retry.error_code, retry.error_kind) == ("failed", "3040", "transient")


async def test_끝이_8888_이면_두_번_대기한_뒤_성공한다():
    gateway = FakeGateway()
    accepted = await gateway.send(_message("01055558888"))
    states = [(await gateway.delivery_state(accepted.provider_message_id)).status for _ in range(3)]
    assert states == ["pending", "pending", "sent"]


async def test_끝이_0000_인데_대체_문자가_있으면_문자로_간_것으로_친다():
    gateway = FakeGateway()
    fallback = FallbackText(from_number="0215550000", text="[두부네] 알림장", channel="lms")
    accepted = await gateway.send(_message("01055550000", fallback))
    state = await gateway.delivery_state(accepted.provider_message_id)
    assert (state.status, state.channel_used, state.error_code) == ("sent", "lms", None)


async def test_잔액은_기본_십만_원이고_생성_인자로_바꾼다():
    assert await FakeGateway().balance() == 100000
    assert await FakeGateway(balance=500).balance() == 500


async def test_호출_기록을_남긴다():
    gateway = FakeGateway()
    await gateway.request_channel_token("@dubu", "01055550000", "001")
    await gateway.send(_message("01055551234"))
    assert gateway.calls[0] == ("request_channel_token", "@dubu", "01055550000", "001")
    assert gateway.calls[1][0] == "send"
