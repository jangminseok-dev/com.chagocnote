"""액세스 토큰 검증 — 모든 라우터가 쓰는 인증 가드.

발급은 auth 스포크 몫이고 여기는 서명 검증과 계정 상태 확인만 한다.
스포크가 auth 를 import 하면 허브-스포크 위반이라 순수 인프라(core)에 둔다.
users 를 원시 SQL 로 조회하는 이유는 core 가 스포크의 ORM 을 import 할 수 없어서다.
"""
from __future__ import annotations

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


def decode_access_token(token: str, public_key: str) -> int:
    try:
        # 허용 알고리즘은 RS256 리터럴로 고정한다 (알고리즘 혼동 공격 방지).
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"], options={"require_exp": True}
        )
        if payload.get("typ") != "access":
            raise ValueError("typ")
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidAccessToken() from exc


async def get_current_user_id(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """서명 검증 + 계정 상태 확인. 정지·탈퇴는 이미 발급된 토큰도 즉시 막는다."""
    if credentials is None:
        raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다.")
    try:
        user_id = decode_access_token(credentials.credentials, JWT_PUBLIC_KEY)
    except InvalidAccessToken:
        raise ApiError(401, "UNAUTHENTICATED", "토큰이 유효하지 않습니다.")
    row = (
        await db.execute(
            text("SELECT suspended_at, deleted_at FROM users WHERE id = :uid"), {"uid": user_id}
        )
    ).first()
    if row is None or row[1] is not None:
        raise ApiError(401, "UNAUTHENTICATED", "유효하지 않은 계정입니다.")
    if row[0] is not None:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "정지된 계정입니다.")
    return user_id
