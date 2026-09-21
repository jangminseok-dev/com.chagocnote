from typing import Literal

from pydantic import BaseModel


class ChangeMemberRoleRequestSchema(BaseModel):
    role: Literal["owner", "staff"]


class ChangedMemberResponseSchema(BaseModel):
    member_id: int
    user_id: int
    role: str
