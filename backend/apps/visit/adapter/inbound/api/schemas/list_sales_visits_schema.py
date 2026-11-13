from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.get_sales_summary_schema import PetCardSchema
from visit.app.dtos.list_sales_visits_dto import SalesVisitsView


class SalesVisitItemSchema(BaseModel):
    visit_id: int
    date: date                  # 방문한 날(매장 시간대)
    pet: PetCardSchema | None   # 보호자만의 방문, 이름을 보일 수 없는 아이면 null
    amount: int | None          # 기록의 총액. 적지 않았으면 null


class SalesVisitsSchema(BaseModel):
    items: list[SalesVisitItemSchema]
    next_cursor: str | None     # 없으면 마지막 쪽

    @classmethod
    def of(cls, view: SalesVisitsView) -> SalesVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
