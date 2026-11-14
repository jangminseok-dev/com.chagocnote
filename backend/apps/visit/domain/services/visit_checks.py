"""예약 앞에서 확인할 것의 판정(③-B 설계 3.1). 순수 함수 — DB 도 시계도 모른다.

막지 않는다. 놓치는 것보다 한 번 더 뜨는 편이 낫다(재현율) — 애매하면 낸다. 기준일은 방문의 날이다.
기준값은 고정이다(매장이 바꾸지 않는다).
"""
from __future__ import annotations

from datetime import date

from visit.domain.value_objects.check_facts import Check, CheckSubject, PetFacts

SENIOR_AGE = 10        # 살
CONSENT_DAYS = 365     # 받은 날로부터 365일째까지 유효
ABSENCE_DAYS = 180     # 마지막 완료 방문이 이보다 오래됐으면 "오랜만"
NO_SHOW_DAYS = 365     # 노쇼를 세는 창(방문 날 앞)

CAUTION, NO_SHOW, FIRST_VISIT = "caution", "no_show", "first_visit"
CONSENT, CONDITIONS, LONG_ABSENCE = "consent", "conditions", "long_absence"
CUSTOMER, PET = "customer", "pet"

# 하루 목록의 "확인 N" 에 세는 것. 지병은 늘 있는 정보라 세지 않는다 — 세면 그 아이의 예약에 표시가 늘 붙는다.
COUNTED = frozenset({CAUTION, NO_SHOW, FIRST_VISIT, CONSENT, LONG_ABSENCE})


def age_on(birth_date: date | None, birth_year: int | None, on: date) -> int | None:
    """그날의 나이. 생일을 알면 만 나이, 출생 연도만 알면 `그 해 − 출생 연도`(생일을 모르면 많게 본다)."""
    if birth_date is not None:
        before_birthday = (on.month, on.day) < (birth_date.month, birth_date.day)
        return on.year - birth_date.year - (1 if before_birthday else 0)
    if birth_year is not None:
        return on.year - birth_year
    return None


def _consent(pet: PetFacts, on: date) -> Check | None:
    reasons = []
    age = age_on(pet.birth_date, pet.birth_year, on)
    if age is not None and age >= SENIOR_AGE:
        reasons.append("senior")
    if pet.conditions:
        reasons.append("conditions")
    if not reasons:
        return None
    if pet.consent_on is None:
        return Check(CONSENT, PET, {"reasons": reasons, "state": "missing", "received_on": None})
    # 받은 날이 방문 날보다 뒤여도(지난 채 남은 예약에서 오늘 받았다) 유효다 — 차이가 음수다.
    if (on - pet.consent_on).days > CONSENT_DAYS:
        return Check(CONSENT, PET, {"reasons": reasons, "state": "expired", "received_on": pet.consent_on})
    return None


def _pet_checks(pet: PetFacts, subject: CheckSubject) -> list[Check]:
    found: list[Check] = []
    if subject.last_completed_on is None:
        found.append(Check(FIRST_VISIT, PET))
    consent = _consent(pet, subject.on)
    if consent is not None:
        found.append(consent)
    if pet.conditions:
        found.append(Check(CONDITIONS, PET, {
            "items": [{"label": label, "note": note} for label, note in pet.conditions],
        }))
    if subject.last_completed_on is not None:
        days = (subject.on - subject.last_completed_on).days
        if days > ABSENCE_DAYS:
            found.append(Check(LONG_ABSENCE, PET, {"days": days, "last_visit_on": subject.last_completed_on}))
    return found


def checks_for(subject: CheckSubject) -> list[Check]:
    """설계 3.1 의 순서 — 주의 · 노쇼 · 첫 방문 · 동의 · 지병 · 오랜만. 보호자 항목이 앞이다."""
    found: list[Check] = []
    if subject.caution is not None:
        found.append(Check(CAUTION, CUSTOMER, {
            "reason": subject.caution.reason, "until": subject.caution.until,
        }))
    if subject.no_show_count > 0:
        found.append(Check(NO_SHOW, CUSTOMER, {"count": subject.no_show_count}))
    # 무지개다리를 건넌 아이의 방문에는 아이 쪽 항목을 내지 않는다.
    if subject.pet is not None and not subject.pet.passed_away:
        found.extend(_pet_checks(subject.pet, subject))
    return found
