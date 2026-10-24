"""솔라피 어댑터 — 실제 API 를 부르지 않고 httpx.MockTransport 로 경로·본문·헤더·오류 분류를 본다.

번호·주소는 테스트 안에서도 가짜 값만 쓴다. 기록(caplog)과 예외 메시지에 번호가 없어야 한다(N12).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
import pytest

from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
from notification.app.ports.output.message_gateway_port import (
    FallbackText,
    GatewayPermanentError,
    GatewayTransientError,
    OutgoingMessage,
)
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import TEMPLATES
from notification.domain.value_objects.message_kind import CONFIRM, REPORT

API_KEY, API_SECRET = "NCS-KEY", "secret-value"
PHONE = "01055550101"
FIXED_NOW = datetime(2026, 10, 14, 1, 2, 3, tzinfo=timezone.utc)
FIXED_SALT = "0123456789abcdef0123456789abcdef"


class _Recorder:
    """받은 요청을 쌓고, 등록한 응답(또는 예외)을 돌려주는 가짜 서버."""

    def __init__(self, *responses) -> None:
        self.requests: list[httpx.Request] = []
        self._responses = list(responses)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def body(self, index: int = 0) -> dict:
        return json.loads(self.requests[index].content)


def _gateway(recorder: _Recorder) -> SolapiGateway:
    return SolapiGateway(
        API_KEY, API_SECRET, transport=httpx.MockTransport(recorder), now=lambda: FIXED_NOW, salt=lambda: FIXED_SALT,
    )


def _ok(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


def _message(**overrides) -> OutgoingMessage:
    fields = dict(
        to=PHONE, provider_channel_id="KA01PF0001", provider_template_id="KA01TP0001",
        variables={"매장명": "두부네", "대상": "두부", "일시": "10월 15일(목) 14:00"}, button_url=None, fallback=None,
    )
    fields.update(overrides)
    return OutgoingMessage(**fields)


_SEND_OK = {"groupInfo": {"groupId": "G1"}, "failedMessageList": [],
            "messageList": [{"messageId": "M1", "statusCode": "2000", "statusMessage": "정상 접수"}]}


# --- 인증 헤더 ---------------------------------------------------------------------------------

async def test_인증_헤더는_HMAC_SHA256_으로_date_와_salt_를_이어_서명한다():
    recorder = _Recorder(_ok({"balance": 1, "point": 0}))
    await _gateway(recorder).balance()
    date = FIXED_NOW.isoformat()
    expected = hmac.new(API_SECRET.encode(), (date + FIXED_SALT).encode(), hashlib.sha256).hexdigest()
    assert recorder.requests[0].headers["Authorization"] == (
        f"HMAC-SHA256 apiKey={API_KEY}, date={date}, salt={FIXED_SALT}, signature={expected}"
    )


async def test_요청마다_새_salt_로_서명하고_기본_주소는_솔라피다():
    recorder = _Recorder(_ok({"balance": 1, "point": 0}), _ok({"balance": 1, "point": 0}))
    gateway = SolapiGateway(API_KEY, API_SECRET, transport=httpx.MockTransport(recorder))
    await gateway.balance()
    await gateway.balance()
    first, second = (r.headers["Authorization"] for r in recorder.requests)
    assert first != second
    assert str(recorder.requests[0].url).startswith("https://api.solapi.com/")


# --- 온보딩 ------------------------------------------------------------------------------------

async def test_토큰_신청은_채널_검색_아이디와_관리자_번호를_보낸다():
    recorder = _Recorder(_ok({"success": True}))
    await _gateway(recorder).request_channel_token("@dubu", PHONE, "001")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("POST", "/kakao/v2/channels/token")
    assert recorder.body() == {"searchId": "@dubu", "phoneNumber": PHONE}


async def test_채널_연동은_토큰까지_보내고_채널_ID_를_돌려준다():
    recorder = _Recorder(_ok({"channelId": "KA01PF0001", "searchId": "@dubu"}))
    channel_id = await _gateway(recorder).link_channel("@dubu", PHONE, "001", "123456")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("POST", "/kakao/v2/channels")
    assert recorder.body() == {"searchId": "@dubu", "phoneNumber": PHONE, "categoryCode": "001", "token": "123456"}
    assert channel_id == "KA01PF0001"


async def test_채널_연동에서_업체가_거절하면_토큰_오류다():
    recorder = _Recorder(httpx.Response(400, json={"errorCode": "ValidationError", "errorMessage": "토큰이 틀립니다"}))
    with pytest.raises(TokenInvalidError):
        await _gateway(recorder).link_channel("@dubu", PHONE, "001", "000000")


async def test_템플릿_등록은_추가한_뒤_검수를_요청하고_템플릿_ID_를_돌려준다():
    recorder = _Recorder(_ok({"templateId": "KA01TP0009", "status": "PENDING"}), _ok({"templateId": "KA01TP0009"}))
    template_id = await _gateway(recorder).register_template("KA01PF0001", TEMPLATES[CONFIRM], 3)
    create, inspect = recorder.requests
    assert (create.method, create.url.path) == ("POST", "/kakao/v2/templates")
    body = recorder.body()
    assert body["channelId"] == "KA01PF0001"
    assert body["name"] == "차곡노트 confirm v3"
    assert body["content"] == TEMPLATES[CONFIRM].body
    assert body["messageType"] == "BA" and body["emphasizeType"] == "NONE" and body["securityFlag"] is False
    assert body["categoryCode"]
    assert "buttons" not in body
    assert (inspect.method, inspect.url.path) == ("PUT", "/kakao/v2/templates/KA01TP0009/inspection")
    assert template_id == "KA01TP0009"


async def test_버튼이_있는_문안은_링크_변수를_쓰는_웹링크_버튼_하나로_등록한다():
    recorder = _Recorder(_ok({"templateId": "KA01TP0010"}), _ok({}))
    await _gateway(recorder).register_template("KA01PF0001", TEMPLATES[REPORT], 1)
    assert recorder.body()["buttons"] == [
        {"buttonType": "WL", "buttonName": "알림장 보기", "linkMo": "#{링크}", "linkPc": "#{링크}"},
    ]


@pytest.mark.parametrize("provider_status, expected", [
    ("PENDING", "pending"), ("INSPECTING", "pending"), ("APPROVED", "approved"),
])
async def test_템플릿_상태를_조회해_셋으로_접는다(provider_status, expected):
    recorder = _Recorder(_ok({"templateId": "KA01TP0001", "status": provider_status, "comments": []}))
    state = await _gateway(recorder).template_state("KA01TP0001")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("GET", "/kakao/v2/templates/KA01TP0001")
    assert (state.status, state.rejected_reason) == (expected, None)


async def test_반려된_템플릿은_마지막_관리자_의견을_사유로_돌려준다():
    recorder = _Recorder(_ok({"status": "REJECTED", "comments": [
        {"isAdmin": False, "memberId": "m", "content": "검수 부탁드려요", "dateCreated": "2026-10-01T00:00:00Z"},
        {"isAdmin": True, "memberId": "a", "content": "변수 비중이 큽니다", "dateCreated": "2026-10-02T00:00:00Z"},
    ]}))
    state = await _gateway(recorder).template_state("KA01TP0001")
    assert (state.status, state.rejected_reason) == ("rejected", "변수 비중이 큽니다")


async def test_발신번호_인증_요청은_번호를_등록하고_인증을_건다():
    recorder = _Recorder(_ok({"phoneNumber": PHONE, "status": "PENDING"}), _ok({"mfa": {"transactionId": "tx-1"}}))
    await _gateway(recorder).request_sender_verification(PHONE)
    register, authenticate = recorder.requests
    assert (register.method, register.url.path) == ("POST", "/senderid/v1/numbers")
    assert recorder.body() == {"phoneNumber": PHONE}
    assert (authenticate.method, authenticate.url.path) == ("PUT", f"/senderid/v1/numbers/{PHONE}/authenticate")
    assert json.loads(authenticate.headers["x-mfa-data"]) == {"authType": "ARS", "extras": {"phoneNumber": PHONE}}


async def test_발신번호_인증_확인은_같은_경로에_거래_ID_와_인증번호를_보낸다():
    recorder = _Recorder(_ok({}), _ok({"mfa": {"transactionId": "tx-1"}}), _ok({"status": "ACTIVE"}))
    gateway = _gateway(recorder)
    await gateway.request_sender_verification(PHONE)
    await gateway.confirm_sender_verification(PHONE, "654321")
    confirm = recorder.requests[2]
    assert (confirm.method, confirm.url.path) == ("PUT", f"/senderid/v1/numbers/{PHONE}/authenticate")
    assert json.loads(confirm.headers["x-mfa-data"]) == {
        "authType": "ARS", "extras": {"phoneNumber": PHONE}, "transactionId": "tx-1", "token": "654321",
    }


async def test_인증번호가_틀리면_토큰_오류다():
    recorder = _Recorder(httpx.Response(400, json={"errorCode": "InvalidToken", "errorMessage": "틀렸습니다"}))
    with pytest.raises(TokenInvalidError):
        await _gateway(recorder).confirm_sender_verification(PHONE, "000000")


# --- 발송 ---------------------------------------------------------------------------------------

async def test_발송은_알림톡_옵션으로_접수하고_변수_키를_업체_형식으로_바꾼다():
    recorder = _Recorder(_ok(_SEND_OK))
    accepted = await _gateway(recorder).send(_message())
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("POST", "/messages/v4/send-many/detail")
    body = recorder.body()
    assert body["showMessageList"] is True
    [message] = body["messages"]
    assert message["to"] == PHONE and message["type"] == "ATA"
    assert message["kakaoOptions"]["pfId"] == "KA01PF0001"
    assert message["kakaoOptions"]["templateId"] == "KA01TP0001"
    assert message["kakaoOptions"]["variables"] == {
        "#{매장명}": "두부네", "#{대상}": "두부", "#{일시}": "10월 15일(목) 14:00",
    }
    assert accepted.provider_message_id == "M1"


async def test_대체_문자가_없으면_disableSms_이고_발신번호와_문구가_없다():
    recorder = _Recorder(_ok(_SEND_OK))
    await _gateway(recorder).send(_message(fallback=None))
    [message] = recorder.body()["messages"]
    assert message["kakaoOptions"]["disableSms"] is True
    assert "from" not in message and "text" not in message


async def test_대체_문자가_있으면_발신번호와_문구를_싣고_disableSms_가_꺼진다():
    recorder = _Recorder(_ok(_SEND_OK))
    fallback = FallbackText(from_number="0215550000", text="[두부네] 10월 15일(목) 14:00 예약이 접수되었어요.", channel="sms")
    await _gateway(recorder).send(_message(fallback=fallback))
    [message] = recorder.body()["messages"]
    assert message["kakaoOptions"]["disableSms"] is False
    assert (message["from"], message["text"]) == (fallback.from_number, fallback.text)


async def test_버튼_주소는_링크_변수로_넘긴다():
    recorder = _Recorder(_ok(_SEND_OK))
    await _gateway(recorder).send(_message(variables={"매장명": "두부네"}, button_url="https://r.example/abc"))
    assert recorder.body()["messages"][0]["kakaoOptions"]["variables"]["#{링크}"] == "https://r.example/abc"


async def test_접수가_거절된_메시지는_업체_상태_코드로_분류한다():
    rejected = {"groupInfo": {"groupId": "G1"}, "messageList": [], "failedMessageList": [
        {"messageId": "M9", "statusCode": "1062", "statusMessage": "발신번호 미등록"}]}
    with pytest.raises(GatewayPermanentError) as permanent:
        await _gateway(_Recorder(_ok(rejected))).send(_message())
    assert permanent.value.code == "1062"
    low_balance = {**rejected, "failedMessageList": [{"messageId": "M9", "statusCode": "1030", "statusMessage": "잔액 부족"}]}
    with pytest.raises(GatewayTransientError) as transient:
        await _gateway(_Recorder(_ok(low_balance))).send(_message())
    assert transient.value.code == "1030"


# --- 상태 조회 ----------------------------------------------------------------------------------

def _listed(status_code: str, message_type: str = "ATA") -> httpx.Response:
    return _ok({"limit": 20, "messageList": {"M1": {"messageId": "M1", "type": message_type, "statusCode": status_code}}})


async def test_상태_조회는_메시지_ID_로_목록을_조회한다():
    recorder = _Recorder(_listed("4000"))
    await _gateway(recorder).delivery_state("M1")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("GET", "/messages/v4/list")
    assert request.url.params["messageId"] == "M1"


@pytest.mark.parametrize("status_code, message_type, expected", [
    ("2000", "ATA", ("pending", None, None, None)),
    ("3000", "ATA", ("pending", None, None, None)),
    ("4000", "ATA", ("sent", "alimtalk", None, None)),
    ("4000", "SMS", ("sent", "sms", None, None)),
    ("4000", "LMS", ("sent", "lms", None, None)),
    ("3104", "ATA", ("failed", None, "3104", "permanent")),   # 카카오톡 미사용자
    ("3107", "ATA", ("failed", None, "3107", "permanent")),   # 알림톡 차단
    ("3010", "ATA", ("failed", None, "3010", "permanent")),   # 수신번호 형식 오류
    ("3103", "ATA", ("failed", None, "3103", "permanent")),   # 템플릿 불일치
    ("3040", "ATA", ("failed", None, "3040", "transient")),   # 전송시간 초과
    ("3041", "ATA", ("failed", None, "3041", "transient")),   # 단말기 busy
    ("3042", "ATA", ("failed", None, "3042", "transient")),   # 음영지역
    ("3024", "ATA", ("failed", None, "3024", "transient")),   # 서버 오류
    ("1030", "ATA", ("failed", None, "1030", "transient")),   # 잔액 부족
    ("9999", "ATA", ("failed", None, "9999", "transient")),   # 표에 없는 코드
])
async def test_업체_상태_코드를_대기_성공_실패로_접는다(status_code, message_type, expected):
    state = await _gateway(_Recorder(_listed(status_code, message_type))).delivery_state("M1")
    assert (state.status, state.channel_used, state.error_code, state.error_kind) == expected


async def test_목록에_아직_없는_메시지는_대기다():
    state = await _gateway(_Recorder(_ok({"limit": 20, "messageList": {}}))).delivery_state("M1")
    assert state.status == "pending"


async def test_잔액은_잔액과_포인트를_더한_원_단위_정수다():
    recorder = _Recorder(_ok({"balance": 12345.5, "point": 100}))
    assert await _gateway(recorder).balance() == 12445
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("GET", "/cash/v1/balance")


# --- 오류 분류 ----------------------------------------------------------------------------------

@pytest.mark.parametrize("failure, code", [
    (httpx.ReadTimeout("timeout"), "NETWORK"),
    (httpx.ConnectError("refused"), "NETWORK"),
    (httpx.Response(500, json={"errorCode": "InternalServerError", "errorMessage": "x"}), "500"),
    (httpx.Response(503, text="bad gateway"), "503"),
    (httpx.Response(429, json={"errorCode": "TooManyRequests", "message": "잦은 호출"}), "429"),
])
async def test_시간_초과_연결_실패_5xx_429_는_일시_오류다(failure, code):
    with pytest.raises(GatewayTransientError) as info:
        await _gateway(_Recorder(failure)).send(_message())
    assert (info.value.code, info.value.kind) == (code, "transient")


async def test_그_밖의_4xx_는_업체_오류_코드를_단_영구_오류다():
    recorder = _Recorder(httpx.Response(400, json={"errorCode": "ValidationError", "errorMessage": "잘못된 요청"}))
    with pytest.raises(GatewayPermanentError) as info:
        await _gateway(recorder).send(_message())
    assert (info.value.code, info.value.kind) == ("ValidationError", "permanent")
    with pytest.raises(GatewayPermanentError) as no_body:
        await _gateway(_Recorder(httpx.Response(403, text="forbidden"))).balance()
    assert no_body.value.code == "403"


async def test_번호는_예외_메시지와_기록에_남지_않는다(caplog):
    """N12 — 요청 본문·경로에 번호가 있어도 예외 메시지와 로그 레코드에는 없다."""
    caplog.set_level(logging.DEBUG)
    recorder = _Recorder(
        httpx.Response(400, json={"errorCode": "ValidationError", "errorMessage": f"수신번호 {PHONE} 오류"}),
        _ok({}), httpx.Response(400, json={"errorCode": "InvalidToken", "errorMessage": PHONE}),
    )
    gateway = _gateway(recorder)
    with pytest.raises(GatewayPermanentError) as send_error:
        await gateway.send(_message())
    with pytest.raises(TokenInvalidError) as token_error:
        await gateway.request_sender_verification(PHONE)
    assert PHONE not in str(send_error.value) and PHONE not in repr(send_error.value)
    assert PHONE not in str(token_error.value)
    assert PHONE in str(recorder.requests[2].url)     # 경로에는 번호가 있다 — 그래서 기록을 본다
    assert all(PHONE not in record.getMessage() for record in caplog.records)
