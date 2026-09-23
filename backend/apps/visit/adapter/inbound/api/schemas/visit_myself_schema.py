from pydantic import BaseModel


class VisitMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
