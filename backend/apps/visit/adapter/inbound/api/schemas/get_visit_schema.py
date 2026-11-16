from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.check_view_schema import CheckSchema
from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
from visit.adapter.inbound.api.schemas.report_view_schema import ReportLinkSchema
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.get_visit_dto import VisitDetailView


class PreviousVisitSchema(BaseModel):
    visit_id: int
    starts_at: datetime
    cover: str | None


class VisitDetailSchema(BaseModel):
    visit: VisitSchema
    group: list[VisitSchema]
    previous_visit: PreviousVisitSchema | None
    no_show_count: int
    record: RecordSchema | None   # 미용 기록 — 없으면 null
    cover: str | None             # 대표 사진 썸네일 URL
    report: ReportLinkSchema      # 알림장 링크의 상태
    checks: list[CheckSchema]     # 확인할 것(③-B) — 살아 있는 방문만
    marks: list[str]              # 끝낸 일의 낱말 코드(⑬) — paid · report_sent 차례
    report_skipped: bool          # 알림장을 보내지 않음으로 넘겼다(⑬) — 되돌릴 수 있다

    @classmethod
    def of(cls, view: VisitDetailView) -> VisitDetailSchema:
        return cls.model_validate(view, from_attributes=True)
