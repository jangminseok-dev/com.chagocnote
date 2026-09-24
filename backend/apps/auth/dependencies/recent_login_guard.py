"""재인증 가드 — 로그인 수단 연결·해제와 회원 탈퇴 앞에서 최근 로그인만 받는다.

토큰 검증은 core(`get_access_claims`)가, 최근인지의 판정은 auth 도메인(`recent_login.is_recent_login`)이 한다.
훔친 액세스 토큰 하나로 계정을 빼앗는 것을 막는다 — 갱신으로 받은 토큰은 통과하지 못한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends

from auth.domain.services.recent_login import is_recent_login
from core.http_errors import ApiError
from core.security import AccessClaims, get_access_claims


@dataclass(frozen=True)
class RecentLogin:
    user_id: int
    auth_time: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def require_recent_login(claims: AccessClaims = Depends(get_access_claims)) -> RecentLogin:
    if not is_recent_login(claims.auth_time, int(_utcnow().timestamp())):
        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
    return RecentLogin(user_id=claims.user_id, auth_time=claims.auth_time)
