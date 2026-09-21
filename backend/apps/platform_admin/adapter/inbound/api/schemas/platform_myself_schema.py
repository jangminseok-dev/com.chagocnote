from pydantic import BaseModel


class PlatformMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
