from pydantic import BaseModel, Field


class UnlinkIdentityResponseSchema(BaseModel):
    identities: list[str]
    access_token: str = Field(description="모든 세션을 끊었다. 이 기기는 이 토큰으로 바꿔 쓴다.")
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
