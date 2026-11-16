from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.list_day_visits_dto import DayVisitsView


class DayCountsSchema(BaseModel):
    visit_count: int   # 마릿수 — 예약됨·미용 중·완료
    reserved: int
    in_progress: int
    completed: int
    canceled: int
    no_show: int
    unresolved: int
    unpaid: int          # 남은 일 — 결제 안 적음(⑬)
    report_unsent: int   # 남은 일 — 알림장 안 보냄(⑬)
    checks: int          # 확인할 것이 있는 살아 있는 방문의 수(⑬)


class DayVisitItemSchema(BaseModel):
    visit: VisitSchema
    group_key: str
    overlapping: bool
    unresolved: bool
    has_record: bool
    cover: str | None   # 대표 사진 썸네일 URL
    report_sent: bool   # 살아 있는 알림장 링크가 있다
    customer_check_count: int   # 확인할 것 가운데 보호자 항목의 수(가족 묶음에서는 한 번만 센다)
    pet_check_count: int        # 아이 항목의 수(지병은 세지 않는다)
    marks: list[str]            # 끝낸 일의 낱말 코드(⑬) — paid · report_sent 차례, 앱은 아는 코드만 쓴다


class DayVisitsSchema(BaseModel):
    date: date
    closed_day: bool
    counts: DayCountsSchema
    items: list[DayVisitItemSchema]

    @classmethod
    def of(cls, view: DayVisitsView) -> DayVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
