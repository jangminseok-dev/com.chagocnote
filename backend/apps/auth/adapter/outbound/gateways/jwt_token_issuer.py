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
    """RS256 액세스 토큰 발급. 유저 ID만 담는다 — 역할과 권한은 매 요청 DB 에서 조회한다."""

    def __init__(
        self, private_key: str, ttl_seconds: int, now: Callable[[], datetime] = _utcnow
    ) -> None:
        self._private_key = private_key
        self._ttl_seconds = ttl_seconds
        self._now = now

    def issue_access(self, user_id: int) -> AccessToken:
        issued_at = self._now()
        claims = {
            "sub": str(user_id),
            "jti": uuid4().hex,
            "typ": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(seconds=self._ttl_seconds)).timestamp()),
        }
        return AccessToken(
            token=jwt.encode(claims, self._private_key, algorithm="RS256"),
            expires_in=self._ttl_seconds,
        )
