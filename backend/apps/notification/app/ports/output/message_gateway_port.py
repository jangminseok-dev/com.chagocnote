"""발송 게이트웨이 포트(설계 6.1) — 업체가 바뀌어도 이 포트만 다시 구현한다.

온보딩(채널 연동·템플릿 등록·발신번호 인증)과 발송·상태 조회·잔액을 한 포트가 낸다. 발송은 접수만 돌려주고
결과는 뒤에 delivery_state 로 본다(웹훅은 첫 판에서 쓰지 않는다).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from notification.domain.services.templates import TemplateText


@dataclass(frozen=True)
class FallbackText:
    """알림톡이 실패했을 때 업체가 보낼 문자. channel 은 "sms" | "lms"."""

    from_number: str
    text: str
    channel: str


@dataclass(frozen=True)
class OutgoingMessage:
    to: str
    provider_channel_id: str
    provider_template_id: str
    variables: Mapping[str, str]       # {"매장명": "…"} — 어댑터가 업체 형식(#{매장명})으로 바꾼다
    button_url: str | None
    fallback: FallbackText | None


@dataclass(frozen=True)
class Accepted:
    provider_message_id: str


@dataclass(frozen=True)
class DeliveryState:
    status: str                        # "pending" | "sent" | "failed"
    channel_used: str | None           # sent 일 때 "alimtalk" | "sms" | "lms"
    error_code: str | None             # failed 일 때 업체 코드
    error_kind: str | None             # failed 일 때 "transient" | "permanent"


@dataclass(frozen=True)
class TemplateState:
    status: str                        # "pending" | "approved" | "rejected"
    rejected_reason: str | None


class GatewayError(Exception):
    """업체 호출 실패의 바탕. code 는 업체 오류 코드 또는 HTTP 상태, kind 는 "transient" | "permanent"."""

    def __init__(self, code: str, kind: str, message: str = "") -> None:
        super().__init__(message or f"업체 호출 실패 ({code})")
        self.code = code
        self.kind = kind


class GatewayTransientError(GatewayError):
    """네트워크·시간 초과·업체 5xx·429·잔액 부족 — 다시 시도한다."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code, "transient", message)


class GatewayPermanentError(GatewayError):
    """그 밖의 4xx — 다시 시도해도 같다."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code, "permanent", message)


class MessageGatewayPort(ABC):
    @abstractmethod
    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None: ...

    @abstractmethod
    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str:
        """provider_channel_id 를 돌려준다. 토큰이 틀리거나 만료됐으면 TokenInvalidError."""

    @abstractmethod
    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str:
        """등록 + 검수 요청. provider_template_id 를 돌려준다."""

    @abstractmethod
    async def template_state(self, provider_template_id: str) -> TemplateState: ...

    @abstractmethod
    async def request_sender_verification(self, phone: str) -> None: ...

    @abstractmethod
    async def confirm_sender_verification(self, phone: str, code: str) -> None:
        """인증번호가 틀리면 TokenInvalidError."""

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> Accepted: ...

    @abstractmethod
    async def delivery_state(self, provider_message_id: str) -> DeliveryState: ...

    @abstractmethod
    async def balance(self) -> int:
        """원."""
