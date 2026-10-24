from pydantic import BaseModel


class MessageCreatedSchema(BaseModel):
    message_id: int
