"""검색 — 가족 한 줄의 검색 문자열을 만들고, 검색어를 낱말로 나눈다.

검색 문자열에는 보호자 이름·초성, 반려동물 이름·초성, 전화 숫자가 들어간다. 보조 연락처는 넣지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from customer.domain.services.hangul_initials import to_initials
from customer.domain.services.phone_number import phone_last4

WordKind = Literal["last4", "phone", "text"]
_LAST4_MAX = 4


@dataclass(frozen=True)
class SearchEntry:
    terms: str
    phone_last4: str
    sort_name: str


@dataclass(frozen=True)
class SearchWord:
    kind: WordKind
    value: str


def build_search_entry(customer_name: str, phone: str, pet_names: list[str]) -> SearchEntry:
    parts: list[str] = []
    for name in (customer_name, *pet_names):
        parts += [name, to_initials(name)]
    parts.append(phone)
    terms = " ".join(dict.fromkeys(parts))   # 순서를 지키며 겹치는 조각(영문 이름의 초성 등)을 뺀다
    return SearchEntry(terms=terms, phone_last4=phone_last4(phone), sort_name=customer_name)


def parse_query(q: str | None) -> tuple[SearchWord, ...]:
    """공백으로 낱말을 나눈다. 숫자(하이픈 허용)만이면 전화 검색 — 4자리 이하는 뒷자리, 그 이상은 전체 번호."""
    words = []
    for raw in (q or "").split():
        digits = raw.replace("-", "")
        if digits and digits.isascii() and digits.isdigit():
            words.append(SearchWord("last4" if len(digits) <= _LAST4_MAX else "phone", digits))
        else:
            words.append(SearchWord("text", raw))
    return tuple(words)
