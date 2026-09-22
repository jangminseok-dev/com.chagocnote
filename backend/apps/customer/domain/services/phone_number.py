"""전화번호 — 숫자만 남겨 검증하고, 목록에 보여 줄 가린 표시를 만든다.

저장·비교는 언제나 숫자만 쓴다. 하이픈·공백·괄호는 입력 편의일 뿐이다.
"""
from __future__ import annotations

import re

from customer.domain.errors import CustomerInputError

# 휴대전화(010·011·016~019), 서울(02), 지역 번호(031~065 범위의 세 자리, 없는 국번 포함), 인터넷 전화(070).
_VALID = re.compile(r"^(01[016789]\d{7,8}|02\d{7,8}|0[3-6][1-5]\d{7,8}|070\d{8})$")


def normalize_phone(raw: str) -> str:
    """숫자만 남긴다. 한국 전화번호 형식이 아니면 CustomerInputError."""
    digits = "".join(ch for ch in raw if ch.isascii() and ch.isdigit())
    if not _VALID.match(digits):
        raise CustomerInputError("전화번호 형식이 올바르지 않습니다.")
    return digits


def _split(digits: str) -> tuple[str, str, str]:
    area = digits[:2] if digits.startswith("02") else digits[:3]
    return area, digits[len(area):-4], digits[-4:]


def format_phone(digits: str) -> str:
    """010-1234-5678 모양. 숫자만 저장된 번호를 보여 줄 때 쓴다."""
    return "-".join(_split(digits))


def mask_phone(digits: str) -> str:
    """가운데 자리의 앞 두 글자만 남기고 가린다. 010-1234-5678 → 010-12··-5678."""
    area, middle, last = _split(digits)
    return f"{area}-{middle[:2]}{'·' * (len(middle) - 2)}-{last}"


def phone_last4(digits: str) -> str:
    return digits[-4:]
