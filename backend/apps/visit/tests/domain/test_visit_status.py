"""상태의 단일 원천 — 표와 상태 클래스가 같은 집합이고, 파생 집합이 성질을 따른다."""
from visit.domain.state.visit_state import _STATES
from visit.domain.state.visit_status import (
    ACTIVE_STATUSES,
    ALL_STATUSES,
    COUNTED_STATUSES,
    STARTED_STATUSES,
    STATUSES,
    status_list_sql,
)


def test_상태마다_상태_클래스가_하나씩_있다():
    assert set(_STATES) == ALL_STATUSES


def test_상태_이름은_서로_다르다():
    assert len({s.code for s in STATUSES}) == len(STATUSES)


def test_파생_집합은_성질을_따른다():
    assert ACTIVE_STATUSES == {"reserved", "in_progress"}
    assert COUNTED_STATUSES == {"reserved", "in_progress", "completed"}
    assert STARTED_STATUSES == {"in_progress", "completed"}


def test_SQL_목록은_표의_순서를_지킨다():
    assert status_list_sql(ALL_STATUSES) == "'reserved', 'in_progress', 'completed', 'canceled', 'no_show'"
    assert status_list_sql(ACTIVE_STATUSES) == "'reserved', 'in_progress'"
