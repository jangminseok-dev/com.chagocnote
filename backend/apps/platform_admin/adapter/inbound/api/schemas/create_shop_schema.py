from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class CreateShopRequestSchema(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    business_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
    ] = "pet_grooming"


class CreateShopResponseSchema(BaseModel):
    shop_id: int
    name: str
    owner_invite_code: str = Field(description="사장에게 전달한다. 이 응답에서 한 번만 볼 수 있다.")
    invite_expires_at: datetime
