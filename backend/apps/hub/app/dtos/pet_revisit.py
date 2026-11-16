from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PetRevisitFact:
    """customer 가 가진 아이의 다시 올 때 사실(⑬) — 직접 정한 주기(주)와 안내한 날. 판정용 돌봄 사실이 아니라
    care_facts 와 따로 읽는다(서명·서류를 읽지 않는 가벼운 읽기)."""

    grooming_cycle_weeks: int | None
    revisit_nudged_on: date | None


@dataclass(frozen=True)
class PetRevisitView:
    """visit 이 계산한 아이의 주기(⑬ 설계 3.1) — 반려동물 상세의 주기 줄이 쓴다. customer 는 계산 규칙을 모른다."""

    cycle_weeks: int                 # 날짜에 쓰는 주(직접·계산이면 그 값, 아니면 매장의 기본 간격)
    cycle_source: str                # manual · computed · single · none
    interval_count: int
    last_interval_weeks: int | None
    last_visit_date: date | None
    due_date: date | None
    estimated: bool
    has_upcoming: bool               # 오늘(매장 시간대) 0시 이후의 예약됨·미용 중이 있다
    nudged_on: date | None           # 안내한 날 — 마지막 완료 방문보다 뒤일 때만(목록과 같은 규칙)
