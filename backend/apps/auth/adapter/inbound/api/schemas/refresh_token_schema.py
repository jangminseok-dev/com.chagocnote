from pydantic import BaseModel, Field


class RefreshRequestSchema(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
