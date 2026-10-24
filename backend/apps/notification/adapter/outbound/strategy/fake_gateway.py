"""dev 와 흐름 테스트용 가짜 게이트웨이 — 외부를 부르지 않고 결정적으로 동작한다.

토큰·인증번호는 000000 만 통과한다. 발송은 늘 접수되고 결과는 번호 끝 네 자리로 가른다 — 0000 영구 실패,
9999 일시 실패, 8888 두 번 대기 뒤 성공, 그 밖은 성공. 끝이 0000 인데 대체 문자가 있으면 문자로 간 것으로 친다.
"""
from __future__ import annotations

from notification.app.ports.output.message_gateway_port import (
    Accepted,
    DeliveryState,
    MessageGatewayPort,
    OutgoingMessage,
    TemplateState,
)
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import TemplateText
from notification.domain.value_objects.message_kind import NEXT_VISIT

FAKE_TOKEN = "000000"
PERMANENT_CODE, TRANSIENT_CODE = "3104", "3040"     # 카카오톡 미사용자, 전송시간 초과


class FakeGateway(MessageGatewayPort):
    def __init__(self, *, reject_next_visit: bool = False, balance: int = 100000) -> None:
        self._reject_next_visit = reject_next_visit
        self._balance = balance
        self.sent_messages: list[OutgoingMessage] = []
        self.calls: list[tuple] = []
        self._polls: dict[str, int] = {}

    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None:
        self.calls.append(("request_channel_token", search_id, admin_phone, category_code))

    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str:
        self.calls.append(("link_channel", search_id, admin_phone, category_code))
        if token != FAKE_TOKEN:
            raise TokenInvalidError("토큰이 틀렸거나 만료되었습니다.")
        return f"pf-{search_id}"

    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str:
        self.calls.append(("register_template", provider_channel_id, template.kind, text_version))
        return f"tpl-{provider_channel_id}-{template.kind}-v{text_version}"

    async def template_state(self, provider_template_id: str) -> TemplateState:
        self.calls.append(("template_state", provider_template_id))
        if self._reject_next_visit and f"-{NEXT_VISIT}-" in provider_template_id:
            return TemplateState(status="rejected", rejected_reason="가짜 반려")
        return TemplateState(status="approved", rejected_reason=None)

    async def request_sender_verification(self, phone: str) -> None:
        self.calls.append(("request_sender_verification", phone))

    async def confirm_sender_verification(self, phone: str, code: str) -> None:
        self.calls.append(("confirm_sender_verification", phone))
        if code != FAKE_TOKEN:
            raise TokenInvalidError("인증번호가 틀렸거나 만료되었습니다.")

    async def send(self, message: OutgoingMessage) -> Accepted:
        self.sent_messages.append(message)
        self.calls.append(("send", message.to, message.provider_template_id))
        return Accepted(provider_message_id=f"fake-{len(self.sent_messages)}")

    async def delivery_state(self, provider_message_id: str) -> DeliveryState:
        self.calls.append(("delivery_state", provider_message_id))
        message = self.sent_messages[int(provider_message_id.removeprefix("fake-")) - 1]
        tail = message.to[-4:]
        if tail == "0000":
            if message.fallback is not None:
                return DeliveryState(status="sent", channel_used=message.fallback.channel, error_code=None,
                                     error_kind=None)
            return DeliveryState(status="failed", channel_used=None, error_code=PERMANENT_CODE, error_kind="permanent")
        if tail == "9999":
            return DeliveryState(status="failed", channel_used=None, error_code=TRANSIENT_CODE, error_kind="transient")
        if tail == "8888":
            self._polls[provider_message_id] = self._polls.get(provider_message_id, 0) + 1
            if self._polls[provider_message_id] <= 2:
                return DeliveryState(status="pending", channel_used=None, error_code=None, error_kind=None)
        return DeliveryState(status="sent", channel_used="alimtalk", error_code=None, error_kind=None)

    async def balance(self) -> int:
        self.calls.append(("balance",))
        return self._balance
