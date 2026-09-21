from __future__ import annotations

from dataclasses import dataclass

from auth.app.dtos.token_dto import TokenPair
from auth.domain.value_objects.identity_revocation import IdentityRevocation


@dataclass(frozen=True)
class UnlinkIdentityCommand:
    user_id: int
    provider: str


@dataclass(frozen=True)
class UnlinkIdentityResult:
    identities: tuple[str, ...]
    tokens: TokenPair                # 모든 세션을 끊었으므로 요청한 기기가 쓸 새 토큰
    revocation: IdentityRevocation   # 커밋 뒤에 제공자 쪽 연결을 끊을 신원
