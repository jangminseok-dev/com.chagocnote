from pydantic import BaseModel, Field


class SocialLoginRequestSchema(BaseModel):
    provider: str = Field(description="kakao · apple · google (개발 환경에서는 dev)")
    token: str = Field(min_length=1, description="제공자 SDK 가 준 토큰. dev 는 로그인할 이름")
    authorization_code: str | None = Field(None, description="Apple 전용")
    nonce: str | None = Field(None, description="Apple 전용 — 앱이 만든 원본 nonce")
    display_name: str | None = Field(None, description="Apple 첫 로그인 때 앱이 받은 이름")


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: int
    is_new_user: bool
