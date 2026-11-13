from pydantic import BaseModel


class GuardianMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
