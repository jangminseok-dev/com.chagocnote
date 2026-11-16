"""예약의 보낼 것 묶음(⑪ 설계 3.5) — 보호자에게 보낼 글을 토막으로 조립한다. 순수 함수.

토막은 `{kind, text}` 다. 뒤의 묶음(예약금 등)이 자기 토막을 더한다.
빈칸이 든 글을 내보내지 않는다 — 값이 없는 자리는 그 둘레(빈 괄호·이름표·붙은 이음표)까지 지우고, 글자가 남지 않은 줄은 뺀다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

RESERVATION, CONSENT = "reservation", "consent"
_WEEKDAYS = "월화수목금토일"
_SLOT = re.compile(r"\{[^{}\s]*\}")
_JOIN = " · "
_EMPTY = "\x00"            # 값이 없는 자리의 표시 — 입력에는 제어 문자가 없다
_BETWEEN = "·,/|"          # 값과 값 사이에 놓는 이음표. 글머리표로 쓰는 `-` 는 넣지 않는다
# 빈 자리의 둘레 — 빈 괄호, 그 값의 이름표(`메뉴: `), 붙은 이음표 하나. 줄의 나머지 글(주소 포함)은 건드리지 않는다.
_EMPTY_BRACKETS = re.compile(rf"\(\s*{_EMPTY}\s*\)|\[\s*{_EMPTY}\s*\]")
_EMPTY_LABELED = re.compile(rf"(?:\s*[{re.escape(_BETWEEN)}])?\s*[^\s{re.escape(_BETWEEN)}:]+:\s*{_EMPTY}")
_EMPTY_AFTER = re.compile(rf"\s*[{re.escape(_BETWEEN)}]\s*{_EMPTY}")
_EMPTY_BEFORE = re.compile(rf"{_EMPTY}\s*[{re.escape(_BETWEEN)}]\s*")
_HAS_TEXT = re.compile(r"[^\W_]")


@dataclass(frozen=True)
class BundlePart:
    kind: str
    text: str


def day_label(at: datetime) -> str:
    return f"{at.month}월 {at.day}일({_WEEKDAYS[at.weekday()]})"


def time_label(at: datetime) -> str:
    half = "오전" if at.hour < 12 else "오후"
    return f"{half} {at.hour % 12 or 12}:{at.minute:02d}"


def fill(template: str, values: dict[str, str]) -> str:
    """자리를 값으로 바꾼다. 모르는 자리는 글자 그대로 둔다(저장할 때 걸러진다). 값에 든 `{…}` 는 다시 채우지 않는다.

    값이 없는 자리는 그 둘레만 정리한다. 정리한 뒤 글자가 남지 않은 줄은 뺀다 — 메뉴가 없는 예약의 메뉴 줄.
    """
    lines = []
    for line in template.split("\n"):
        filled = _SLOT.sub(lambda m: (values[m.group()] or _EMPTY) if m.group() in values else m.group(), line)
        if _EMPTY in filled:
            for pattern in (_EMPTY_BRACKETS, _EMPTY_LABELED, _EMPTY_AFTER, _EMPTY_BEFORE):
                filled = pattern.sub("", filled)
            filled = re.sub(r" {2,}", " ", filled.replace(_EMPTY, "")).strip()
            if not _HAS_TEXT.search(filled):
                continue
        lines.append(filled.rstrip())
    return "\n".join(lines).strip()


def build_bundle(
    *, shop_name: str, pet_names: list[str], starts_at: datetime, menu_names: list[str],
    reservation_text: str, consent_text: str, consent_pet_names: list[str], consent_url: str | None,
) -> list[BundlePart]:
    """starts_at 은 매장 시간대의 시각이다. consent_url 이 없으면 동의서 토막이 없다."""
    parts = []
    reservation = fill(reservation_text, {
        "{매장}": shop_name, "{아이}": _JOIN.join(pet_names), "{날짜}": day_label(starts_at),
        "{시간}": time_label(starts_at), "{메뉴}": _JOIN.join(menu_names),
    })
    if reservation:
        parts.append(BundlePart(RESERVATION, reservation))
    if consent_url:
        consent = fill(consent_text, {
            "{매장}": shop_name, "{아이}": _JOIN.join(consent_pet_names), "{링크}": consent_url,
        })
        if consent:
            parts.append(BundlePart(CONSENT, consent))
    return parts
