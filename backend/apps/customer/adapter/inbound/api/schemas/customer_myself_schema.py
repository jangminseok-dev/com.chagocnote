from pydantic import BaseModel


class CustomerMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
