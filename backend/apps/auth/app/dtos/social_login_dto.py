from __future__ import annotations

from dataclasses import dataclass

from auth.app.dtos.token_dto import TokenPair


@dataclass(frozen=True)
class SocialLoginCommand:
    provider: str
    token: str
    authorization_code: str | None
    nonce: str | None
    display_name: str | None


@dataclass(frozen=True)
class SocialLoginResult:
    user_id: int
    is_new_user: bool
    tokens: TokenPair
