from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SocialCredentials:
    """앱이 제공자 SDK 에서 받아 서버로 넘긴 값. 서버는 이것을 제공자에게 직접 확인한다."""

    token: str = field(repr=False)
    # Apple 전용 — 리프레시 토큰으로 교환한다
    authorization_code: str | None = field(default=None, repr=False)
    nonce: str | None = None               # Apple 전용 — 앱이 만든 원본 nonce
    display_name: str | None = None        # Apple 은 첫 로그인 때만 이름을 앱에 준다
