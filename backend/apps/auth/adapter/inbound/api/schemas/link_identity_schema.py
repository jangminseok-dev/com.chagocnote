from pydantic import BaseModel, Field


class LinkIdentityRequestSchema(BaseModel):
    provider: str = Field(description="kakao · apple · google (개발 환경에서는 dev)")
    token: str = Field(min_length=1, description="제공자 SDK 가 준 토큰. dev 는 붙일 이름")
    authorization_code: str | None = Field(None, description="Apple 전용")
    nonce: str | None = Field(None, description="Apple 전용 — 앱이 만든 원본 nonce")


class IdentitiesResponseSchema(BaseModel):
    identities: list[str]
