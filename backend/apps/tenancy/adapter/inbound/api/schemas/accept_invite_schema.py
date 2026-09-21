from typing import Annotated

from pydantic import BaseModel, StringConstraints


class AcceptInviteRequestSchema(BaseModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class AcceptInviteResponseSchema(BaseModel):
    shop_id: int
    shop_name: str
    role: str
    member_id: int
