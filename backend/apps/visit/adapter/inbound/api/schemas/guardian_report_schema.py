"""보호자(로그인)에게 나가는 지난 알림장 목록. 한 장은 공개 알림장의 스키마(`PublicReportSchema`)를 그대로 쓴다 —
보호자용 알림장 스키마를 따로 만들지 않는다(새 칸을 더하는 것은 공개 범위를 넓히는 일이다)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class _Guardian(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GuardianPetSchema(_Guardian):
    pet_id: int
    name: str | None


class GuardianPetListSchema(BaseModel):
    items: list[GuardianPetSchema]


class GuardianCoverSchema(_Guardian):
    url: str
    width: int
    height: int


class GuardianReportItemSchema(_Guardian):
    report_id: int
    visit_date: date
    pet_id: int | None               # 보호자만의 방문이면 null
    pet_name: str | None
    cover: GuardianCoverSchema | None
    media_count: int


class GuardianReportPageSchema(BaseModel):
    items: list[GuardianReportItemSchema]
    next_cursor: str | None
