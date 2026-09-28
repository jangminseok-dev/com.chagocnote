"""매장용 알림장 응답 모양(app 의 report_view_dto 와 짝). 끈 항목의 칸은 null 이다.

공개 응답은 따로 둔다 — 거기에는 media_id·hidden 이 없고 끈 항목은 칸이 아예 없다.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ReportMediaSchema(BaseModel):
    media_id: int
    kind: str                 # photo · video
    phase: str                # before · after
    hidden: bool              # 알림장에서 뺀 것
    width: int
    height: int
    duration_seconds: int | None
    display_url: str          # 사진은 표시용, 영상은 원본(재생용)
    thumb_url: str            # 영상이면 포스터
    download_url: str


class ReportCoverSchema(BaseModel):
    url: str
    width: int
    height: int


class ReportMenuSchema(BaseModel):
    name: str
    amount: int | None


class ReportShopSchema(BaseModel):
    name: str
    phone: str | None
    address: str | None


class ReportSchema(BaseModel):
    pet_name: str | None
    visit_date: date
    care_note: str | None
    media: list[ReportMediaSchema]   # 후 → 전, 그 안에서 순서대로
    cover: ReportCoverSchema | None
    menus: list[ReportMenuSchema] | None
    total_amount: int | None
    weight_kg: float | None          # JSON 숫자로 내보낸다(기록 응답과 같은 관례)
    shop: ReportShopSchema | None


class ReportLinkSchema(BaseModel):
    status: str                      # none · live
    url: str | None
    expires_at: datetime | None      # null 이면 기간이 없다
    first_viewed_at: datetime | None
    created_at: datetime | None
