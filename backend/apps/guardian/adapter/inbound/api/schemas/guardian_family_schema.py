from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, StrictInt


class FamilyInviteSchema(BaseModel):
    """만든 초대 — 코드는 이 응답에만 있다. 웹 서버가 받아 주소(`/j/<코드>`)를 만들고 기록하지 않는다."""

    code: str
    expires_at: datetime


class FamilyMemberSchema(BaseModel):
    """가족 한 사람 — 이름·계정 없이 이은 날만."""

    family_id: int
    linked_at: datetime
    unseen: bool


class FamilyListSchema(BaseModel):
    items: list[FamilyMemberSchema]


class GuardianSettingsDefaultsSchema(BaseModel):
    family_max: int


class GuardianSettingsSchema(BaseModel):
    family_max: int                       # 고객 한 명당 함께 볼 수 있는 가족 수(0 이면 초대가 없다)
    defaults: GuardianSettingsDefaultsSchema


class UpdateGuardianSettingsRequestSchema(BaseModel):
    family_max: StrictInt                 # 범위(0~10)는 도메인이 본다
