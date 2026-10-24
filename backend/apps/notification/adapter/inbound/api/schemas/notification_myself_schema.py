from pydantic import BaseModel


class NotificationMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
