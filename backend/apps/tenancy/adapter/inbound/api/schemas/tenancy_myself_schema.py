from pydantic import BaseModel


class TenancyMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
