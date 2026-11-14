from pydantic import BaseModel


class SearchMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
