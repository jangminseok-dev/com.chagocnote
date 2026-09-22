"""액세스 토큰 검증 — 모든 라우터가 쓰는 인증 가드.

발급은 auth 스포크 몫이고 여기는 서명 검증과 계정 상태 확인만 한다.
스포크가 auth 를 import 하면 허브-스포크 위반이라 순수 인프라(core)에 둔다.
users 를 원시 SQL 로 조회하는 이유는 core 가 스포크의 ORM 을 import 할 수 없어서다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text

from core.config import JWT_PUBLIC_KEY
from core.database import DbSession
from core.http_errors import ApiError

_bearer = HTTPBearer(auto_error=False)


class InvalidAccessToken(Exception):
    pass


RECENT_LOGIN_SECONDS = 300
# 발급 프로세스와 검증 프로세스의 시계 차로 봐줄 수 있는 폭. 이보다 먼 미래의 로그인 시각은 믿지 않는다.
MAX_CLOCK_SKEW_SECONDS = 60


@dataclass(frozen=True)
class AccessClaims:
    user_id: int
    auth_time: int | None  # 소셜 로그인으로 받은 토큰에만 있다 (갱신으로 받은 토큰에는 없다)


@dataclass(frozen=True)
class RecentLogin:
    user_id: int
    auth_time: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def decode_access_claims(token: str, public_key: str) -> AccessClaims:
    try:
        # 허용 알고리즘은 RS256 리터럴로 고정한다 (알고리즘 혼동 공격 방지).
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"], options={"require_exp": True}
        )
        if payload.get("typ") != "access":
            raise ValueError("typ")
        auth_time = payload.get("auth_time")
        # bool 은 int 의 하위 타입이라 따로 거른다.
        if auth_time is not None and (isinstance(auth_time, bool) or not isinstance(auth_time, int)):
            raise ValueError("auth_time")
        return AccessClaims(user_id=int(payload["sub"]), auth_time=auth_time)
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidAccessToken() from exc


def decode_access_token(token: str, public_key: str) -> int:
    return decode_access_claims(token, public_key).user_id


async def _authenticate(db, credentials: HTTPAuthorizationCredentials | None) -> AccessClaims:
    """서명 검증 + 계정 상태 확인. 정지·탈퇴는 이미 발급된 토큰도 즉시 막는다."""
    if credentials is None:
        raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다.")
    try:
        claims = decode_access_claims(credentials.credentials, JWT_PUBLIC_KEY)
    except InvalidAccessToken:
        raise ApiError(401, "UNAUTHENTICATED", "토큰이 유효하지 않습니다.")
    row = (
        await db.execute(
            text("SELECT suspended_at, deleted_at FROM users WHERE id = :uid"),
            {"uid": claims.user_id},
        )
    ).first()
    if row is None or row[1] is not None:
        raise ApiError(401, "UNAUTHENTICATED", "유효하지 않은 계정입니다.")
    if row[0] is not None:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "정지된 계정입니다.")
    return claims


async def get_current_user_id(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    return (await _authenticate(db, credentials)).user_id


async def require_recent_login(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> RecentLogin:
    """로그인 수단 연결·해제와 회원 탈퇴 앞의 재인증. 소셜 로그인한 지 RECENT_LOGIN_SECONDS 안의
    토큰만 받는다. 훔친 액세스 토큰 하나로 계정을 빼앗는 것을 막는다 — 갱신으로 받은 토큰은 통과하지 못한다."""
    claims = await _authenticate(db, credentials)
    if claims.auth_time is None:
        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
    elapsed = int(_utcnow().timestamp()) - claims.auth_time
    if elapsed > RECENT_LOGIN_SECONDS or elapsed < -MAX_CLOCK_SKEW_SECONDS:
        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
    return RecentLogin(user_id=claims.user_id, auth_time=claims.auth_time)
