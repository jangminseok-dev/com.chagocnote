from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GuardianLinkCreatedSchema(BaseModel):
    link_id: int


class GuardianLinkItemSchema(BaseModel):
    link_id: int
    shop_name: str
    linked_at: datetime


class GuardianLinkListSchema(BaseModel):
    items: list[GuardianLinkItemSchema]


class CustomerGuardianLinkSchema(BaseModel):
    """매장이 보는 연결 — 여부와 날짜뿐이다. 보호자가 누구인지는 싣지 않는다(⑦ 설계 G14)."""

    linked: bool
    linked_at: datetime | None
