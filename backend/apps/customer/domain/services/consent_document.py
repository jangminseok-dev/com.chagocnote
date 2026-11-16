"""동의서 한 장의 조립과 지문(⑪ 설계 3.2·3.3). 순수 함수.

문안은 열 때 조립한다 — 보낸 뒤 지병이 더해졌으면 보호자는 더해진 것을 읽는다.
낼 때는 열 때의 지문과 다시 계산한 지문을 견준다 — 하나라도 다르면 받지 않는다.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date

from customer.domain.entities.consent import ConsentPolicy, DocumentPet, PetConsentFacts
from customer.domain.errors import CustomerInputError
from customer.domain.services.consent_coverage import needed_parts, uncovered

__all__ = ["base_date", "build_document", "doc_digest", "needed_parts"]


def base_date(today: date, for_date: date | None, policy: ConsentPolicy) -> date:
    """문서를 조립하는 기준일. 예약 날을 주면 그날에 유효한 동의를 지금 받는다 — 그날 기한이 지나는지, 그날 노령인지로 본다.

    지난 날은 오늘로 본다. 기한보다 먼 날은 받지 않는다(그날의 동의는 어차피 다시 받아야 한다).
    예약 앞의 확인할 것(visit)이 방문의 날로 판정하는 것과 맞물린다.
    """
    if for_date is None or for_date <= today:
        return today
    if (for_date - today).days > policy.consent_days:
        raise CustomerInputError("기준일이 너무 멉니다.")
    return for_date


def build_document(
    pets: Sequence[PetConsentFacts], on: date, policy: ConsentPolicy,
) -> tuple[DocumentPet, ...]:
    """아이별 구역. 다시 받을 토막이 없는 아이와 무지개다리 아이는 뺀다. pet_id 오름차순."""
    found = []
    for facts in sorted(pets, key=lambda f: f.pet_id):
        if facts.passed_away:
            continue
        parts, full = uncovered(facts, on, policy)
        if parts:
            found.append(DocumentPet(
                pet_id=facts.pet_id, name=facts.name, condition_labels=facts.condition_labels,
                parts=parts, full=full))
    return tuple(found)


def doc_digest(doc: Sequence[DocumentPet], versions: Mapping[str, tuple[str, int]]) -> str:
    """보호자가 본 것의 지문. versions 는 토막 → (글의 출처 default·shop, 판).

    아이의 이름·남은 토막·그 토막의 글의 판·지병 이름 목록이 하나라도 다르면 지문이 다르다.
    """
    material = [
        [pet.pet_id, pet.name, list(pet.parts), [[part, *versions[part]] for part in pet.parts],
         list(pet.condition_labels)]
        for pet in sorted(doc, key=lambda p: p.pet_id)
    ]
    raw = json.dumps(material, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
