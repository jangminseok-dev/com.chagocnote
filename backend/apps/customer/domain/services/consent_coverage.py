"""지금의 동의가 무엇을 덮는가(⑪ 설계 3.3). 순수 함수 — DB 도 시계도 모른다.

서명으로 받은 동의는 읽은 토막과 그때 보인 지병 이름이 남아 있어 바뀐 것만 다시 받는다.
손으로 적은 동의는 무엇을 읽었는지 기록이 없어 토막을 가르지 않는다(③-B 의 동작 그대로 — 지병이 늘면 수정 유스케이스가 받은 날을 지운다).
"""
from __future__ import annotations

from datetime import date

from customer.domain.entities.consent import ConsentPolicy, PetConsentFacts
from customer.domain.services.pet_age import age_years


def needed_parts(facts: PetConsentFacts, on: date, policy: ConsentPolicy) -> tuple[str, ...]:
    """그날 이 아이에게 필요한 토막. basic 은 늘, senior 는 노령, condition 은 지병이 하나라도."""
    parts = ["basic"]
    age = age_years(facts.birth_date, facts.birth_year, on)
    if age is not None and age >= policy.senior_age:
        parts.append("senior")
    if facts.condition_labels:
        parts.append("condition")
    return tuple(parts)


def uncovered(facts: PetConsentFacts, on: date, policy: ConsentPolicy) -> tuple[tuple[str, ...], bool]:
    """(다시 받을 토막, 전체를 다시 받는가). 전체를 다시 받으면 서명이 받은 날을 새로 찍는다."""
    needed = needed_parts(facts, on, policy)
    # 받은 날이 그날보다 뒤여도 유효다(차이가 음수) — ③-B 와 같다.
    if facts.consent_on is None or (on - facts.consent_on).days > policy.consent_days:
        return needed, True
    if not facts.via_signature:
        return (), False
    left = []
    if "senior" in needed and not any("senior" in cover.parts for cover in facts.signed):
        left.append("senior")
    if "condition" in needed:
        shown = frozenset().union(*(cover.condition_labels for cover in facts.signed)) if facts.signed else frozenset()
        if not set(facts.condition_labels) <= shown:
            left.append("condition")
    return tuple(left), False
