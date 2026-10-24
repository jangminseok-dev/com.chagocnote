"""문안 6종과 변수(설계 6.3). 문안은 코드에 고정이고 변수만 채운다 — 바꾸면 TEXT_VERSION 을 올려 전 매장에 다시 등록한다.

변수 이름은 한글 그대로(`#{매장명}` …). 알림톡 본문의 알림장 주소는 버튼에만 있고(`#{링크}` 는 sms_body 에만), 업체는
변수 값을 글자 그대로 넣으므로 이름에 `#{` 가 있어도 문안이 깨지지 않는다 — render 도 한 번만 치환한다.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT

TEXT_VERSION = 1
MAX_VARIABLE_CHARS = 200     # 업체의 변수 길이 한도 안에서 자른다. 주소(#{링크})는 자르지 않는다
SMS_MAX_BYTES = 90           # EUC-KR 바이트. 넘으면 LMS
URL_VARIABLE = "링크"
WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")
PLACEHOLDER = re.compile(r"#\{([^}]+)\}")


@dataclass(frozen=True)
class TemplateText:
    kind: str
    name: str
    body: str                    # 알림톡 본문. 줄바꿈은 "\n"
    sms_body: str                # 문자 대체용 짧은 문안
    button_label: str | None     # 버튼은 report 만 — 주소는 #{링크} 변수


TEMPLATES: dict[str, TemplateText] = {
    CONFIRM: TemplateText(
        kind=CONFIRM, name="예약 접수 안내",
        body="[#{매장명}] 예약 접수 안내\n#{대상}의 예약이 접수되었어요.\n일시: #{일시}\n변경·취소는 매장으로 연락해 주세요.",
        sms_body="[#{매장명}] #{일시} 예약이 접수되었어요.", button_label=None,
    ),
    REMINDER: TemplateText(
        kind=REMINDER, name="내일 예약 안내",
        body="[#{매장명}] 내일 예약 안내\n#{대상}의 예약이 내일이에요.\n일시: #{일시}\n늦거나 못 오시면 미리 연락해 주세요.",
        sms_body="[#{매장명}] 내일 #{시각} 예약을 잊지 마세요.", button_label=None,
    ),
    REPORT: TemplateText(
        kind=REPORT, name="미용 알림장",
        body="[#{매장명}] 미용 알림장\n#{대상}의 오늘 미용 알림장이 도착했어요.\n#{기간안내}",
        sms_body="[#{매장명}] 알림장 #{링크}", button_label="알림장 보기",
    ),
    CHANGE: TemplateText(
        kind=CHANGE, name="예약 변경 안내",
        body="[#{매장명}] 예약 변경 안내\n#{대상}의 예약 일시가 바뀌었어요.\n변경 전: #{이전일시}\n변경 후: #{일시}",
        sms_body="[#{매장명}] 예약이 #{일시}로 바뀌었어요.", button_label=None,
    ),
    CANCEL: TemplateText(
        kind=CANCEL, name="예약 취소 안내",
        body="[#{매장명}] 예약 취소 안내\n매장 사정으로 #{대상}의 #{일시} 예약이 취소되었어요. 죄송합니다.\n"
             "다시 예약하시려면 매장으로 연락해 주세요.",
        sms_body="[#{매장명}] #{일시} 예약이 매장 사정으로 취소되었어요.", button_label=None,
    ),
    NEXT_VISIT: TemplateText(
        kind=NEXT_VISIT, name="미용 주기 안내",
        body="[#{매장명}] 미용 주기 안내\n#{대상}의 지난 미용이 #{지난일}이었어요.\n#{간격}주 정도마다 미용하면 좋아요.\n"
             "예약은 매장으로 연락해 주세요.",
        sms_body="[#{매장명}] #{대상} 미용한 지 #{간격}주가 지났어요.", button_label=None,
    ),
}


@dataclass(frozen=True)
class RenderedMessage:
    text: str
    sms_text: str
    button_url: str | None
    variables: Mapping[str, str]     # 업체에 넘길 #{이름}: 값


def target_label(pet_name: str | None, customer_name: str) -> str:
    """반려동물 이름이 있으면 그대로, 없으면 보호자 이름 뒤에 '님'."""
    return pet_name if pet_name else f"{customer_name}님"


def _local(at: datetime, tz: str) -> datetime:
    return at.astimezone(ZoneInfo(tz))


def format_date(at: datetime, tz: str) -> str:
    local = _local(at, tz)
    return f"{local.month}월 {local.day}일({WEEKDAYS[local.weekday()]})"


def format_time(at: datetime, tz: str) -> str:
    return _local(at, tz).strftime("%H:%M")


def format_when(at: datetime, tz: str) -> str:
    return f"{format_date(at, tz)} {format_time(at, tz)}"


def expiry_label(expires_at: datetime | None, tz: str) -> str:
    if expires_at is None:
        return "언제든 열 수 있어요."
    local = _local(expires_at, tz)
    return f"{local.month}월 {local.day}일까지 열려요."


def _placeholders(text: TemplateText) -> list[str]:
    """문안(본문·문자용·버튼)이 쓰는 변수 이름, 나온 순서대로 한 번씩."""
    names = PLACEHOLDER.findall(text.body) + PLACEHOLDER.findall(text.sms_body)
    if text.button_label is not None:
        names.append(URL_VARIABLE)
    return list(dict.fromkeys(names))


def variables_for(kind: str, *, shop_name: str, target: str, starts_at: datetime, tz: str,
                  previous_starts_at: datetime | None = None, url: str | None = None,
                  expires_at: datetime | None = None, last_visit_at: datetime | None = None,
                  interval_weeks: int | None = None) -> dict[str, str]:
    """종류의 문안이 쓰는 변수만 돌려준다. 그 종류에 필요한 값이 빠져 있으면 ValueError(프로그래밍 오류)."""
    known: dict[str, str] = {
        "매장명": shop_name,
        "대상": target,
        "일시": format_when(starts_at, tz),
        "시각": format_time(starts_at, tz),
        "기간안내": expiry_label(expires_at, tz),
    }
    if previous_starts_at is not None:
        known["이전일시"] = format_when(previous_starts_at, tz)
    if url is not None:
        known[URL_VARIABLE] = url
    if last_visit_at is not None:
        known["지난일"] = format_date(last_visit_at, tz)
    if interval_weeks is not None:
        known["간격"] = str(interval_weeks)
    variables = {}
    for name in _placeholders(TEMPLATES[kind]):
        if name not in known:
            raise ValueError(f"{kind} 문안의 변수 {name} 에 넣을 값이 없습니다.")
        variables[name] = known[name]
    return variables


def _clip(name: str, value: str) -> str:
    return value if name == URL_VARIABLE else value[:MAX_VARIABLE_CHARS]


def render(kind: str, variables: Mapping[str, str]) -> RenderedMessage:
    """#{x} 를 값으로 치환한다. 한 번만 — 값에 '#{' 가 있어도 다시 치환하지 않는다."""
    text = TEMPLATES[kind]
    values = {name: _clip(name, value) for name, value in variables.items()}

    def fill(match: re.Match) -> str:
        name = match.group(1)
        if name not in values:
            raise ValueError(f"{kind} 문안의 변수 {name} 이 비어 있습니다.")
        return values[name]

    return RenderedMessage(
        text=PLACEHOLDER.sub(fill, text.body),
        sms_text=PLACEHOLDER.sub(fill, text.sms_body),
        button_url=values[URL_VARIABLE] if text.button_label is not None else None,
        variables={f"#{{{name}}}": value for name, value in values.items()},
    )


def euc_kr_bytes(text: str) -> int:
    return len(text.encode("euc-kr", errors="replace"))


def sms_channel(sms_text: str) -> str:
    """EUC-KR 바이트 90 이하면 sms, 넘으면 lms."""
    return "sms" if euc_kr_bytes(sms_text) <= SMS_MAX_BYTES else "lms"
