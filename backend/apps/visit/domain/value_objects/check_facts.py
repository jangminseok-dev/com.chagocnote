from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class CautionMark:
    reason: str
    until: date


@dataclass(frozen=True)
class PetFacts:
    """판정에 쓰는 아이의 사실. 지병은 (이름, 메모)."""

    birth_date: date | None
    birth_year: int | None
    conditions: tuple[tuple[str, str | None], ...]
    consent_on: date | None
    passed_away: bool


@dataclass(frozen=True)
class CheckSubject:
    """방문 하나(또는 아직 없는 예약의 아이 하나)에 대한 사실 묶음."""

    on: date                          # 방문의 날(매장 시간대) — 모든 판정의 기준일
    pet: PetFacts | None              # 보호자만의 방문이거나 아이를 읽지 못했으면 None
    caution: CautionMark | None       # 보호자의 살아 있는 주의 표시
    no_show_count: int                # 방문 날 앞 365일의 노쇼
    last_completed_on: date | None    # 이 방문 앞의 마지막 완료 방문의 날. 없으면 None(첫 방문)


@dataclass(frozen=True)
class Check:
    """확인할 것 하나. detail 의 칸은 code 마다 다르다."""

    code: str      # caution · no_show · first_visit · consent · conditions · long_absence
    scope: str     # customer | pet
    detail: dict = field(default_factory=dict)
