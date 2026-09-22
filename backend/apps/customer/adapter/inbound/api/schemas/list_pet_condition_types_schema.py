from pydantic import BaseModel


class ConditionTypeSchema(BaseModel):
    code: str
    label: str
    sort_order: int
