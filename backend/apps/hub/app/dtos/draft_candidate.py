from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.family_brief import CustomerBrief, PetBrief


@dataclass(frozen=True)
class DraftCandidate:
    """카톡 예약 초안의 "누구" 후보 — 글의 낱말에 걸린 가족 하나.

    pets 는 무지개다리를 건너지 않은 아이만이다. matched_pet_ids 는 글의 낱말과 이름이 정확히 같은 아이,
    exact 는 반려동물이나 보호자 이름이 정확히 일치했는지(아니면 전화·부분 일치)다.
    """

    customer: CustomerBrief
    pets: tuple[PetBrief, ...]
    matched_pet_ids: tuple[int, ...]
    exact: bool
