"""하루 목록과 달력의 표시 — 정리 안 된 예약, 가족 묶음, 겹침, 상태별 수. 저장하지 않고 계산한다."""
from __future__ import annotations

from collections import Counter
from datetime import date

from visit.domain.entities.visit import COMPLETED, IN_PROGRESS, RESERVED, Visit
from visit.domain.services.visit_schedule import local_date

# 마릿수로 치는 상태 — 취소·노쇼는 그날 한 일이 아니다.
COUNTED = frozenset({RESERVED, IN_PROGRESS, COMPLETED})


def is_unresolved(visit: Visit, today: date, tz: str) -> bool:
    """지난 날(매장 시간대로 오늘 이전)인데 아직 예약됨 — 완료를 깜빡했거나 되돌린 방문이다."""
    return visit.status == RESERVED and local_date(visit.starts_at, tz) < today


def overlaps_other_group(visit: Visit, occupied: list[Visit]) -> bool:
    """살아 있는 방문이 다른 가족 묶음과 시간이 겹치는가. 끝난 방문(완료·취소·노쇼)은 겹침을 따지지 않는다."""
    return visit.is_active and any(
        o.id != visit.id and o.group_key != visit.group_key
        and o.starts_at < visit.ends_at and visit.starts_at < o.ends_at
        for o in occupied
    )


def status_counts(visits: list[Visit]) -> Counter:
    return Counter(v.status for v in visits)
