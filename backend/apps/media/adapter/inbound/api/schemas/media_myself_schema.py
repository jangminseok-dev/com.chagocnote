from pydantic import BaseModel


class MediaMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
