from datetime import datetime

from pydantic import BaseModel, Field


class CreateInviteResponseSchema(BaseModel):
    code: str = Field(description="직원에게 전달한다. 이 응답에서 한 번만 볼 수 있다.")
    role: str
    expires_at: datetime
