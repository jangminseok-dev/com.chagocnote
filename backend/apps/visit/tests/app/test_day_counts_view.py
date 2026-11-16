"""하루 집계 칸과 상태 표가 같은 집합인지 — 상태를 더하고 칸을 잊으면(또는 상태가 아닌 칸을 더하면) 여기서 걸린다."""
from dataclasses import fields

from visit.app.dtos.list_day_visits_dto import _NOT_STATUS, DayCountsView
from visit.domain.state.visit_status import ALL_STATUSES


def test_하루_집계의_상태_칸은_상태_표와_같은_집합이다():
    # 상태가 아닌 칸 — 마릿수, 정리 안 됨, 남은 일 둘과 확인할 것(⑬).
    assert set(_NOT_STATUS) == {"unresolved", "unpaid", "report_unsent", "checks"}
    status_fields = {f.name for f in fields(DayCountsView)} - {"visit_count", *_NOT_STATUS}
    assert status_fields == ALL_STATUSES
