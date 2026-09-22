"""문자열 입력의 NUL·제어 문자를 막는 공용 검증기.

NUL 이나 제어 문자가 그대로 DB 에 닿으면 asyncpg 가 DBAPIError 를 일으켜 500 이 된다(Important 1 의
원인). 여기서 422 로 미리 막는다. 메모는 개행만 예외로 허용한다.
"""
from __future__ import annotations

import unicodedata


def reject_control_chars(value: str | None, *, allow_newline: bool = False) -> str | None:
    if value is None:
        return value
    for ch in value:
        if allow_newline and ch == "\n":
            continue
        if unicodedata.category(ch) == "Cc":
            raise ValueError("NUL·제어 문자를 포함할 수 없습니다.")
    return value
