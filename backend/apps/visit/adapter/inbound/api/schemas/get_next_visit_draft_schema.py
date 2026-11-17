from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import MenuBriefSchema
from visit.app.dtos.get_next_visit_draft_dto import NextVisitDraftView


class RepeatDraftSchema(BaseModel):
    interval_weeks: int
    count: int
    starts_at: datetime


class NextVisitDraftSchema(BaseModel):
    customer_id: int
    pet_ids: list[int]
    starts_at: datetime
    duration_minutes: int
    menus: list[MenuBriefSchema]
    interval_weeks: int     # (예전 앱이 읽는 칸 — cycle_weeks 와 같다)
    cycle_weeks: int        # 날짜에 쓴 주(⑬)
    cycle_source: str       # manual · computed · single · none
    upcoming_starts_at: datetime | None   # 그 아이들의 뒤 예약(⑭) — 있으면 완료 시트의 기본 버튼이 [완료]
    repeat: RepeatDraftSchema | None      # 묶음의 마지막 회차면 같은 조건으로 이어 잡기(⑭)

    @classmethod
    def of(cls, view: NextVisitDraftView) -> NextVisitDraftSchema:
        return cls.model_validate(view, from_attributes=True)
