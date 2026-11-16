from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CautionFact:
    """보호자의 살아 있는 주의 표시. 이 매장 안에서만 쓴다 — 로그·공개 응답에 싣지 않는다."""

    reason: str
    until: date


@dataclass(frozen=True)
class ConditionFact:
    label: str            # 정해진 종류의 이름, 기타면 직접 적은 이름
    note: str | None


@dataclass(frozen=True)
class ConsentCover:
    """서명으로 받은 미용 동의가 덮는 것(⑪) — 받은 날부터의 서명들을 합친 것.

    basic 은 늘 덮였다. 손으로 적은 동의에는 이 값이 없다(무엇을 읽었는지 기록이 없다).
    """

    senior: bool                          # 노령 토막을 읽고 서명했는가
    condition_labels: frozenset[str]      # 서명할 때 보인 지병 이름들


@dataclass(frozen=True)
class PetCareFact:
    """예약 앞에서 확인할 것을 판정하는 데 쓰는 아이의 사실."""

    pet_id: int
    customer_id: int
    birth_date: date | None
    birth_year: int | None
    conditions: tuple[ConditionFact, ...]   # 종류의 순서대로
    consent_on: date | None                 # 미용 동의를 가장 최근에 받은 날
    passed_away: bool
    consent_cover: ConsentCover | None = None      # 서명으로 받은 동의일 때만 값이 있다
    consent_form_sent_on: date | None = None       # 살아 있는 동의서 링크가 있으면 보낸 날(매장 시간대)


@dataclass(frozen=True)
class CareFacts:
    """고객·아이의 사실 묶음. 익명화한 고객과 그 아이, 다른 매장의 것, 없는 ID 는 빠진다."""

    known_customers: frozenset[int]         # 살아 있는 이 매장의 고객
    cautions: dict[int, CautionFact]        # 고객 ID → 살아 있는 주의 표시만
    pets: dict[int, PetCareFact]
