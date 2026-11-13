from __future__ import annotations

from pydantic import BaseModel, Field


class SetCustomerCautionRequestSchema(BaseModel):
    # 길이의 정확한 판정(앞뒤 공백을 뗀 뒤 1~100자)은 도메인이 한다. 여기서는 터무니없이 긴 본문만 막는다.
    reason: str = Field(max_length=300)
