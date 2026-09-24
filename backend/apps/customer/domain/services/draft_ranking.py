"""카톡 예약 초안의 "누구" 후보 순위 — 낱말이 가족의 어디에 맞았는지로 등급을 매긴다.

등급 0 반려동물 이름 정확 일치 → 1 보호자 이름 정확 일치 → 2 전화(8자리 이상 포함 / 4자리 뒷자리) → 3 부분 일치
(검색이 걸어 준 가족이지만 위 셋에 해당하지 않음). 0·1 이 "정확"이다. 같은 등급 안의 순서(고객 ID)는 부르는 쪽이
정한다. 낱말은 여기서 저장하지도 기록하지도 않는다.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet

PET_NAME = 0
CUSTOMER_NAME = 1
PHONE = 2
PARTIAL = 3


@dataclass(frozen=True)
class FamilyMatch:
    rank: int
    matched_pet_ids: tuple[int, ...]

    @property
    def exact(self) -> bool:
        return self.rank <= CUSTOMER_NAME


def phone_digits(words: Sequence[str]) -> list[str]:
    """낱말 가운데 숫자만인 것(하이픈은 뗀다) — 전화 일치에 쓴다."""
    return [w.replace("-", "") for w in words if w.replace("-", "").isdigit()]


def match_family(customer: Customer, pets: Sequence[Pet], words: Sequence[str]) -> FamilyMatch:
    """가족 하나의 등급과, 이름이 맞은 반려동물 ID(등급 0 일 때만 비어 있지 않다)."""
    matched = tuple(p.id for p in pets if p.name in words)
    if matched:
        return FamilyMatch(PET_NAME, matched)
    if customer.name in words:
        return FamilyMatch(CUSTOMER_NAME, ())
    digits = phone_digits(words)
    if any((len(d) >= 8 and d in customer.phone) or (len(d) == 4 and customer.phone.endswith(d)) for d in digits):
        return FamilyMatch(PHONE, ())
    return FamilyMatch(PARTIAL, ())
