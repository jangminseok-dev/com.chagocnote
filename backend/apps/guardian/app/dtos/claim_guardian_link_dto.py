from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClaimGuardianLinkCommand:
    user_id: int
    token: str | None = field(repr=False)   # 알림장 토큰 — 로그·예외 메시지에 찍히지 않게 막는다


@dataclass(frozen=True)
class ClaimGuardianLinkResult:
    link_id: int
    created: bool   # False 면 이미 내 연결이었다
