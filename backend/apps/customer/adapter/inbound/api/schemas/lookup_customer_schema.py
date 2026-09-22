from pydantic import BaseModel


class LookupCustomerResponseSchema(BaseModel):
    customer_id: int
    name: str
    pet_names: list[str]
