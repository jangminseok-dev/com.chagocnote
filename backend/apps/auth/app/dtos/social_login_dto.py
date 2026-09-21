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


@dataclass(frozen=True)
class SocialLoginResult:
    user_id: int
    is_new_user: bool
    tokens: TokenPair
