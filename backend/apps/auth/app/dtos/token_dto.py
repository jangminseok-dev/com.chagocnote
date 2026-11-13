from dataclasses import dataclass, field


@dataclass(frozen=True)
class AccessToken:
    token: str = field(repr=False)   # 원문이 로그·예외 메시지에 찍히지 않게 막는다
    expires_in: int


@dataclass(frozen=True, repr=False)
class TokenPair:
    """로그인·갱신·해제가 발급하는 우리 쪽 토큰 쌍. repr 에 원문이 찍히지 않게 막아 둔다.

    보호자 웹 세션은 리프레시 토큰이 없다(None) — 그 밖의 발급은 늘 있다."""

    access_token: str
    refresh_token: str | None
    expires_in: int

    def __repr__(self) -> str:
        return f"TokenPair(expires_in={self.expires_in})"
