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
from customer.domain.services.consent_coverage import needed_parts, uncovered

__all__ = ["build_document", "doc_digest", "needed_parts"]


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
