from pydantic import BaseModel


class AuthMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
