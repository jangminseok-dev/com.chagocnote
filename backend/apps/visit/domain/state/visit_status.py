"""방문 상태의 단일 원천 — 상태 이름과 그 성질(살아 있는가, 마릿수로 세는가, 시작 시각이 있는가).

상태를 더하면 여기에 한 줄을 더하고 `visit_state.py`에 상태 클래스를 하나 더한다. 그러면 나머지는 따라온다:
- `ACTIVE_STATUSES`·`COUNTED_STATUSES`·`STARTED_STATUSES`는 성질에서 파생한다.
- ORM 의 CHECK 와 부분 색인은 `status_list_sql()`로 문자열을 만든다(마이그레이션은 손으로 써야 한다 —
  `tests/test_schema_drift.py`는 CHECK·부분 색인을 비교하지 않으므로, `tests/integration/test_visit_status_schema.py`가
  실제 DB 의 CHECK·부분 색인을 표와 대조해 알려 준다).
- 하루 집계(`DayCountsView.of`)는 상태 이름을 열거하지 않는다.
- `tests/domain/test_visit_status.py`가 상태 클래스와 이 표가 같은 집합인지 확인한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisitStatus:
    code: str
    is_active: bool          # 시간을 차지하고 '앞으로의 예약'으로 센다
    counts_as_visit: bool    # 하루·달력의 마릿수로 센다 — 취소·노쇼는 그날 한 일이 아니다
    has_started_at: bool     # 이 상태면 started_at 이 있어야 한다(CHECK)


RESERVED = "reserved"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
CANCELED = "canceled"
NO_SHOW = "no_show"

# 순서는 ORM CHECK 문자열의 순서다(마이그레이션 0006 과 같게 둔다).
STATUSES: tuple[VisitStatus, ...] = (
    VisitStatus(RESERVED, is_active=True, counts_as_visit=True, has_started_at=False),
    VisitStatus(IN_PROGRESS, is_active=True, counts_as_visit=True, has_started_at=True),
    VisitStatus(COMPLETED, is_active=False, counts_as_visit=True, has_started_at=True),
    VisitStatus(CANCELED, is_active=False, counts_as_visit=False, has_started_at=False),
    VisitStatus(NO_SHOW, is_active=False, counts_as_visit=False, has_started_at=False),
)
ALL_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES)
ACTIVE_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES if s.is_active)
COUNTED_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES if s.counts_as_visit)
STARTED_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES if s.has_started_at)


def status_list_sql(codes: frozenset[str]) -> str:
    """CHECK·부분 색인에 넣을 `'a', 'b'` 문자열. 표의 순서를 지킨다."""
    return ", ".join(f"'{s.code}'" for s in STATUSES if s.code in codes)
