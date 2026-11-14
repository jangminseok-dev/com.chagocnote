"""미용 동의와 주의 표시의 규칙(③-B 설계 3.2·3.3). 순수 함수다.

기준값은 고정이다 — 매장이 바꾸지 않는다. 주의 표시는 기한이 지나도 지우지 않고 읽을 때 거른다.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from customer.domain.errors import CustomerInputError

CAUTION_DAYS = 365
REASON_MAX = 100


def clean_reason(text: str) -> str:
    """앞뒤 공백을 떼고 1~100자인지 본다. 사유는 오류 메시지에 싣지 않는다."""
    reason = text.strip()
    if not 1 <= len(reason) <= REASON_MAX:
        raise CustomerInputError("주의 사유는 1자에서 100자 사이여야 합니다.")
    return reason


def caution_until(today: date) -> date:
    """달거나 고친 날로부터 365일 뒤."""
    return today + timedelta(days=CAUTION_DAYS)


def caution_active(until: date | None, today: date) -> bool:
    """끝나는 날 당일까지 살아 있다."""
    return until is not None and until >= today


def check_consent_day(received_on: date, today: date) -> None:
    if received_on > today:
        raise CustomerInputError("동의를 받은 날은 오늘보다 뒤일 수 없습니다.")


def conditions_added(before: Iterable, after: Iterable) -> bool:
    """지병이 하나라도 늘었나 — (종류, 직접 적은 이름)으로 견준다. 빼거나 메모만 고친 것은 아니다.

    늘었으면 앞서 받은 미용 동의가 새 지병을 덮지 않으므로 동의를 비운다.
    """
    known = {(c.type_code, c.custom_label) for c in before}
    return any((c.type_code, c.custom_label) not in known for c in after)
