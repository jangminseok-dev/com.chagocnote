from __future__ import annotations

from dataclasses import dataclass, field

from auth.app.dtos.token_dto import TokenPair


@dataclass(frozen=True)
class SocialLoginCommand:
    provider: str
    token: str = field(repr=False)
    authorization_code: str | None = field(repr=False)
    nonce: str | None
    display_name: str | None
    session: str | None = None   # "web" 이면 보호자 웹 세션(30분, 리프레시 없음). 없으면 매장 앱의 세션


@dataclass(frozen=True)
class SocialLoginResult:
    user_id: int
    is_new_user: bool
    tokens: TokenPair
