from __future__ import annotations

from dataclasses import dataclass

from auth.app.dtos.token_dto import TokenPair
from auth.domain.value_objects.identity_revocation import IdentityRevocation


@dataclass(frozen=True)
class UnlinkIdentityCommand:
    user_id: int
    provider: str
    auth_time: int   # 요청 토큰의 로그인 시각. 새 토큰이 그대로 물려받는다 (해제를 되풀이해 늘릴 수 없게)


@dataclass(frozen=True)
class UnlinkIdentityResult:
    identities: tuple[str, ...]
    tokens: TokenPair                # 모든 세션을 끊었으므로 요청한 기기가 쓸 새 토큰
    revocation: IdentityRevocation   # 커밋 뒤에 제공자 쪽 연결을 끊을 신원
