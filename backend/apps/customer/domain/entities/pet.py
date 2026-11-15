from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class PetCondition:
    """반려동물이 가진 질병 한 항목. label 은 정해진 종류의 이름이다(기타면 '기타')."""

    type_code: str
    label: str
    custom_label: str | None
    note: str | None
    # 지병 행의 ID — 검색 문서의 원본 ID 로 쓴다(⑨). 같은 지병인지 견줄 때는 보지 않는다(수정하면 행이 새로 생긴다).
    condition_id: int = field(default=0, compare=False)


@dataclass(frozen=True)
class Pet:
    id: int
    customer_id: int
    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    weight_kg: Decimal
    no_known_conditions: bool
    memo: str | None
    passed_away_at: datetime | None
    conditions: tuple[PetCondition, ...]
    grooming_consent_on: date | None = None   # 미용 동의를 가장 최근에 받은 날(③-B)
    grooming_consent_signature_id: int | None = None   # 그날을 찍은 서명(⑪). 손으로 적은 동의면 None

    @property
    def has_conditions(self) -> bool:
        return bool(self.conditions)

    @property
    def passed_away(self) -> bool:
        return self.passed_away_at is not None
