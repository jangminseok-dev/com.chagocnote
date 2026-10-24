"""솔라피(api.solapi.com) 어댑터 — HMAC-SHA256 서명, 알림톡 접수, 상태 조회, 채널·템플릿·발신번호 온보딩.

경로·본문 키는 공식 SDK(solapi-nodejs·solapi-kotlin·solapi-php)와 개발자 문서에서 읽은 것이다(T6 보고서 7절).
요청 본문(번호·변수)·헤더·응답 본문은 로그에 찍지 않고, 예외 메시지에는 업체 코드만 넣는다(N12).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from notification.app.ports.output.message_gateway_port import (
    Accepted,
    DeliveryState,
    GatewayPermanentError,
    GatewayTransientError,
    MessageGatewayPort,
    OutgoingMessage,
    TemplateState,
)
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import URL_VARIABLE, TemplateText

# httpx 는 요청 URL 을 INFO 로 기록한다 — 발신번호 인증 경로에 번호가 들어 있어 끈다(N12).
logging.getLogger("httpx").setLevel(logging.WARNING)

# 알림톡 템플릿 카테고리 코드 — 실계정에서 GET /kakao/v2/templates/categories 로 확인해 맞춘다(T6 보고서 7절).
TEMPLATE_CATEGORY_CODE = "003001"

# 업체 4자리 상태 코드 → (status, channel_used, error_kind). sent 의 channel_used 는 메시지 type 으로 정한다.
# 표에 없는 실패 코드는 transient(다시 시도하는 쪽이 싸다 — 3회 뒤 멈춘다). 출처: solapi.com/guides/message-status-codes
_PENDING = ("pending", None, None)
_SENT = ("sent", None, None)
_PERMANENT = ("failed", None, "permanent")
_TRANSIENT = ("failed", None, "transient")
_DELIVERY: dict[str, tuple[str, str | None, str | None]] = {
    "2000": _PENDING, "3000": _PENDING,
    "4000": _SENT,
    # 입력·설정 오류, 수신 거부, 수신번호 오류, 카카오톡 미사용·차단, 템플릿 불일치
    "1010": _PERMANENT, "1011": _PERMANENT, "1026": _PERMANENT, "1041": _PERMANENT, "1042": _PERMANENT,
    "1043": _PERMANENT, "1057": _PERMANENT, "1060": _PERMANENT, "1061": _PERMANENT, "1062": _PERMANENT,
    "1065": _PERMANENT, "2061": _PERMANENT, "2062": _PERMANENT, "2065": _PERMANENT, "3010": _PERMANENT,
    "3013": _PERMANENT, "3031": _PERMANENT, "3032": _PERMANENT, "3047": _PERMANENT, "3052": _PERMANENT,
    "3061": _PERMANENT, "3101": _PERMANENT, "3102": _PERMANENT, "3103": _PERMANENT, "3104": _PERMANENT,
    "3105": _PERMANENT, "3106": _PERMANENT, "3107": _PERMANENT, "3117": _PERMANENT,
    # 잔액 부족, 서버 오류, 전송시간 초과, 단말기 사정, 음영지역, 발송 가능 시간 아님
    "1024": _TRANSIENT, "1030": _TRANSIENT, "2024": _TRANSIENT, "2025": _TRANSIENT, "2230": _TRANSIENT,
    "3012": _TRANSIENT, "3024": _TRANSIENT, "3040": _TRANSIENT, "3041": _TRANSIENT, "3042": _TRANSIENT,
    "3043": _TRANSIENT, "3044": _TRANSIENT, "3045": _TRANSIENT, "3046": _TRANSIENT, "3053": _TRANSIENT,
    "3056": _TRANSIENT, "3057": _TRANSIENT, "3108": _TRANSIENT,
}
_CHANNEL_BY_TYPE = {"ATA": "alimtalk", "SMS": "sms", "LMS": "lms"}
_TEMPLATE_STATUS = {"PENDING": "pending", "INSPECTING": "pending", "APPROVED": "approved", "REJECTED": "rejected"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _salt() -> str:
    return secrets.token_hex(16)


class SolapiGateway(MessageGatewayPort):
    """transport·now·salt 는 테스트 주입용이다(httpx.MockTransport, 고정 시각·솔트로 서명을 검증한다)."""

    def __init__(
        self, api_key: str, api_secret: str, *, base_url: str = "https://api.solapi.com",
        transport: httpx.AsyncBaseTransport | None = None, timeout: float = 10.0,
        now: Callable[[], datetime] = _utc_now, salt: Callable[[], str] = _salt,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._now = now
        self._salt = salt
        self._http = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=timeout)
        self._mfa_transactions: dict[str, str] = {}     # 발신번호 → 인증 거래 ID (요청과 확인 사이에만 든다)

    # --- 인증 -----------------------------------------------------------------------------------

    def _authorization(self) -> str:
        date = self._now().isoformat()
        salt = self._salt()
        signature = hmac.new(self._api_secret.encode(), (date + salt).encode(), hashlib.sha256).hexdigest()
        return f"HMAC-SHA256 apiKey={self._api_key}, date={date}, salt={salt}, signature={signature}"

    async def _call(self, method: str, path: str, *, json_body: dict | None = None, params: dict | None = None,
                    headers: dict[str, str] | None = None, token_errors: bool = False) -> dict:
        """호출하고 JSON 을 돌려준다. 실패는 GatewayError 로, token_errors 면 4xx 를 TokenInvalidError 로 바꾼다."""
        request_headers = {"Authorization": self._authorization(), **(headers or {})}
        try:
            response = await self._http.request(method, path, json=json_body, params=params, headers=request_headers)
        except httpx.TimeoutException as exc:
            raise GatewayTransientError("NETWORK", "업체 응답 시간 초과") from exc
        except httpx.TransportError as exc:
            raise GatewayTransientError("NETWORK", "업체에 연결할 수 없습니다.") from exc
        status = response.status_code
        if status == 429 or status >= 500:
            raise GatewayTransientError(str(status))
        if status >= 400:
            code = _error_code(response) or str(status)
            if token_errors and status != 401:
                raise TokenInvalidError(f"업체가 토큰을 거절했습니다 ({code}).")
            raise GatewayPermanentError(code)
        return response.json() if response.content else {}

    # --- 온보딩 ---------------------------------------------------------------------------------

    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None:
        await self._call("POST", "/kakao/v2/channels/token", json_body={"searchId": search_id, "phoneNumber": admin_phone})

    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str:
        body = {"searchId": search_id, "phoneNumber": admin_phone, "categoryCode": category_code, "token": token}
        created = await self._call("POST", "/kakao/v2/channels", json_body=body, token_errors=True)
        return created["channelId"]

    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str:
        body: dict = {
            "channelId": provider_channel_id,
            "name": f"차곡노트 {template.kind} v{text_version}",
            "content": template.body,
            "categoryCode": TEMPLATE_CATEGORY_CODE,
            "messageType": "BA",
            "emphasizeType": "NONE",
            "securityFlag": False,
        }
        if template.button_label is not None:
            link = f"#{{{URL_VARIABLE}}}"
            body["buttons"] = [{"buttonType": "WL", "buttonName": template.button_label, "linkMo": link, "linkPc": link}]
        created = await self._call("POST", "/kakao/v2/templates", json_body=body)
        template_id = created["templateId"]
        await self._call("PUT", f"/kakao/v2/templates/{template_id}/inspection", json_body={})
        return template_id

    async def template_state(self, provider_template_id: str) -> TemplateState:
        found = await self._call("GET", f"/kakao/v2/templates/{provider_template_id}")
        status = _TEMPLATE_STATUS[found["status"]]
        reason = None
        if status == "rejected":
            admin_comments = [c.get("content") for c in found.get("comments") or [] if c.get("isAdmin")]
            reason = admin_comments[-1] if admin_comments else "반려됨"
        return TemplateState(status=status, rejected_reason=reason)

    async def request_sender_verification(self, phone: str) -> None:
        await self._call("POST", "/senderid/v1/numbers", json_body={"phoneNumber": phone}, token_errors=True)
        mfa = {"authType": "ARS", "extras": {"phoneNumber": phone}}
        started = await self._call("PUT", f"/senderid/v1/numbers/{phone}/authenticate",
                                   headers={"x-mfa-data": json.dumps(mfa)}, token_errors=True)
        transaction_id = (started.get("mfa") or {}).get("transactionId")
        if transaction_id:
            self._mfa_transactions[phone] = transaction_id

    async def confirm_sender_verification(self, phone: str, code: str) -> None:
        mfa: dict = {"authType": "ARS", "extras": {"phoneNumber": phone}}
        if phone in self._mfa_transactions:
            mfa["transactionId"] = self._mfa_transactions[phone]
        mfa["token"] = code
        await self._call("PUT", f"/senderid/v1/numbers/{phone}/authenticate",
                         headers={"x-mfa-data": json.dumps(mfa)}, token_errors=True)
        self._mfa_transactions.pop(phone, None)

    # --- 발송·상태·잔액 -------------------------------------------------------------------------

    async def send(self, message: OutgoingMessage) -> Accepted:
        variables = {f"#{{{name}}}": value for name, value in message.variables.items()}
        if message.button_url is not None:
            variables[f"#{{{URL_VARIABLE}}}"] = message.button_url
        kakao: dict = {
            "pfId": message.provider_channel_id,
            "templateId": message.provider_template_id,
            "variables": variables,
            "disableSms": message.fallback is None,
        }
        item: dict = {"to": message.to, "type": "ATA", "kakaoOptions": kakao}
        if message.fallback is not None:
            item["from"] = message.fallback.from_number
            item["text"] = message.fallback.text
        result = await self._call("POST", "/messages/v4/send-many/detail",
                                  json_body={"messages": [item], "showMessageList": True})
        failed = result.get("failedMessageList") or []
        if failed:
            code = str(failed[0].get("statusCode") or "")
            if _DELIVERY.get(code, _TRANSIENT)[2] == "transient":
                raise GatewayTransientError(code)
            raise GatewayPermanentError(code)
        return Accepted(provider_message_id=result["messageList"][0]["messageId"])

    async def delivery_state(self, provider_message_id: str) -> DeliveryState:
        listed = await self._call("GET", "/messages/v4/list", params={"messageId": provider_message_id})
        found = (listed.get("messageList") or {}).get(provider_message_id)
        if found is None:
            return DeliveryState(status="pending", channel_used=None, error_code=None, error_kind=None)
        code = str(found.get("statusCode") or "")
        status, channel_used, error_kind = _DELIVERY.get(code, _TRANSIENT)
        if status == "sent":
            message_type = str(found.get("type") or "")
            channel_used = _CHANNEL_BY_TYPE.get(message_type, message_type.lower())
        return DeliveryState(status=status, channel_used=channel_used,
                             error_code=code if status == "failed" else None, error_kind=error_kind)

    async def balance(self) -> int:
        found = await self._call("GET", "/cash/v1/balance")
        return int((found.get("balance") or 0) + (found.get("point") or 0))


def _error_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    code = body.get("errorCode") if isinstance(body, dict) else None
    return str(code) if code else None
