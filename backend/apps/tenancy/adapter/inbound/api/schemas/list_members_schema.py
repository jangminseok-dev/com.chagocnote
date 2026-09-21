from datetime import datetime

from pydantic import BaseModel


class MemberSchema(BaseModel):
    member_id: int
    user_id: int
    display_name: str
    profile_image_url: str | None
    role: str
    joined_at: datetime
