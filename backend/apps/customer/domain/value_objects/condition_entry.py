from __future__ import annotations

from dataclasses import dataclass

OTHER = "other"   # 직접 입력하는 질병 종류 코드. pet_condition_types 시드에 있다.


@dataclass(frozen=True)
class ConditionEntry:
    """반려동물이 가진 질병 한 항목. 정해진 종류면 custom_label 이 없고, 기타면 있다."""

    type_code: str
    custom_label: str | None
    note: str | None
