"""예약의 보낼 것 묶음(⑪ 설계 3.5) — 보호자에게 보낼 글을 토막으로 조립한다. 순수 함수.

토막은 `{kind, text}` 다. 뒤의 묶음(예약금 등)이 자기 토막을 더한다.
빈칸이 든 글을 내보내지 않는다 — 값이 없는 자리만 든 줄은 빼고, 한 줄에 섞인 빈 자리는 흔적(가운뎃점·쉼표)까지 지운다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

RESERVATION, CONSENT = "reservation", "consent"
_WEEKDAYS = "월화수목금토일"
_SLOT = re.compile(r"\{[^{}\s]*\}")
_JOIN = " · "
# 빈 자리가 남긴 이음표 — 줄의 맨 앞·맨 뒤, 그리고 나란히 겹친 것(뒤의 것을 남긴다).
_SEPARATORS = "·,/|-"
_EDGE = re.compile(rf"^[\s{re.escape(_SEPARATORS)}]+|[\s{re.escape(_SEPARATORS)}]+$")
_DOUBLED = re.compile(rf"(?:[{re.escape(_SEPARATORS)}]\s*)+([{re.escape(_SEPARATORS)}])")


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
    """자리를 값으로 바꾼다. 모르는 자리는 글자 그대로 둔다(저장할 때 걸러진다)."""
    lines = []
    for line in template.split("\n"):
        slots = [slot for slot in _SLOT.findall(line) if slot in values]
        if slots and not any(values[slot] for slot in slots):
            continue      # 값이 없는 자리만 든 줄 — 메뉴가 없는 예약의 메뉴 줄
        emptied = False
        for slot in slots:
            emptied = emptied or not values[slot]
            line = line.replace(slot, values[slot])
        if emptied:
            line = _EDGE.sub("", _DOUBLED.sub(r"\1", line))
            line = re.sub(r"\s{2,}", " ", line)
        lines.append(line.rstrip())
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
