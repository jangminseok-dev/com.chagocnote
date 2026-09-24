from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import CustomerBriefSchema, PetBriefSchema
from visit.app.dtos.list_visit_feed_dto import VisitFeedView


class FeedItemSchema(BaseModel):
    visit_id: int
    customer: CustomerBriefSchema
    pet: PetBriefSchema | None
    completed_at: datetime      # 매장 시간대
    cover: str | None           # 대표 사진 썸네일 URL — 없으면 회색 자리
    menus: list[str]            # 기록의 실제 메뉴, 없으면 예약 메뉴
    care_note: str | None       # 앞 80자
    media_count: int


class VisitFeedSchema(BaseModel):
    items: list[FeedItemSchema]
    next_cursor: str | None     # 없으면 마지막 쪽

    @classmethod
    def of(cls, view: VisitFeedView) -> VisitFeedSchema:
        return cls.model_validate(view, from_attributes=True)
