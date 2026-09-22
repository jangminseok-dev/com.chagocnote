"""한글 초성 — 콩이 → ㅋㅇ. 초성 검색에 쓴다."""
from __future__ import annotations

_INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_FIRST, _LAST = 0xAC00, 0xD7A3
_PER_INITIAL = 21 * 28  # 중성 21 × 종성 28


def to_initials(text: str) -> str:
    """한글 음절을 초성으로 바꾼다. 한글 음절이 아닌 글자(영문·숫자·자모)는 그대로 둔다."""
    return "".join(
        _INITIALS[(ord(ch) - _FIRST) // _PER_INITIAL] if _FIRST <= ord(ch) <= _LAST else ch
        for ch in text
    )
