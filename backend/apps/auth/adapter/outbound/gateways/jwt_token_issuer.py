from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt

from auth.app.dtos.token_dto import AccessToken
from auth.app.ports.output.token_issuer_port import TokenIssuerPort


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JwtTokenIssuer(TokenIssuerPort):
    """RS256 액세스 토큰 발급. 유저 ID 와 (소셜 로그인일 때) 로그인 시각만 담는다 — 역할과 권한은 매 요청 DB 에서 조회한다."""

    def __init__(
        self, private_key: str, ttl_seconds: int, now: Callable[[], datetime] = _utcnow
    ) -> None:
        self._private_key = private_key
        self._ttl_seconds = ttl_seconds
        self._now = now

    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False
    ) -> AccessToken:
        issued_at = self._now()
        iat = int(issued_at.timestamp())
        claims = {
            "sub": str(user_id),
            "jti": uuid4().hex,
            "typ": "access",
            "iat": iat,
            "exp": int((issued_at + timedelta(seconds=self._ttl_seconds)).timestamp()),
        }
        # 최근 로그인 확인(재인증)에 쓴다. 갱신으로 받은 토큰에는 없다.
        if fresh_login:
            claims["auth_time"] = iat
        elif auth_time is not None:
            claims["auth_time"] = auth_time
        return AccessToken(
            token=jwt.encode(claims, self._private_key, algorithm="RS256"),
            expires_in=self._ttl_seconds,
        )
