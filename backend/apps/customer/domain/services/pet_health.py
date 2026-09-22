"""질병 규칙 — 질병이 있거나, '질병 없음'을 직접 확인했거나 둘 중 하나다.

두 표(pets.no_known_conditions 와 pet_conditions 행)에 걸친 규칙이라 CHECK 로 쓸 수 없어 여기서 확인한다.
"""
from __future__ import annotations

from customer.domain.errors import (
    CustomerInputError,
    PetHealthConflictError,
    PetHealthRequiredError,
)
from customer.domain.value_objects.condition_entry import OTHER, ConditionEntry


def check_conditions(
    conditions: tuple[ConditionEntry, ...], no_known_conditions: bool, known_codes: frozenset[str]
) -> None:
    if not conditions and not no_known_conditions:
        raise PetHealthRequiredError("질병을 고르거나 '질병 없음'을 눌러 주세요.")
    if conditions and no_known_conditions:
        raise PetHealthConflictError("질병을 고르면서 '질병 없음'을 함께 누를 수 없습니다.")
    seen: set[str] = set()
    for entry in conditions:
        if entry.type_code not in known_codes:
            raise CustomerInputError("알 수 없는 질병 종류입니다.")
        if (entry.type_code == OTHER) != (entry.custom_label is not None):
            raise CustomerInputError("'기타'일 때만 질병 이름을 직접 입력합니다.")
        if entry.type_code != OTHER:
            if entry.type_code in seen:
                raise CustomerInputError("같은 질병을 두 번 넣을 수 없습니다.")
            seen.add(entry.type_code)
