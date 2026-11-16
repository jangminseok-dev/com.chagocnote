from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from visit.domain.services.visit_cycle import PetCycle


@dataclass(frozen=True)
class RevisitCandidate:
    """다시 올 때가 됐을지도 모르는 아이 — 마지막 완료 방문이 한 해 안이고 앞으로 잡힌 예약이 없다(⑬ 설계 3.3)."""

    pet_id: int
    last_visit_id: int    # 마지막 완료 방문 — [예약]이 그 방문의 다음 예약 초안을 쓴다
    last_day: date        # 그 방문의 날(매장 시간대)


@dataclass(frozen=True)
class RevisitRow:
    pet_id: int
    bucket: str           # soon · due
    cycle: PetCycle
    last_visit_id: int
    nudged_on: date | None   # 안내한 날 — 마지막 완료 방문보다 뒤일 때만(다녀가면 저절로 사라진다)
