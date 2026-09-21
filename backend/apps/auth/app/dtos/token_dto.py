from dataclasses import dataclass


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_in: int


@dataclass(frozen=True, repr=False)
class TokenPair:
    """로그인·갱신·해제가 발급하는 우리 쪽 토큰 쌍. repr 에 원문이 찍히지 않게 막아 둔다."""

    access_token: str
    refresh_token: str
    expires_in: int

    def __repr__(self) -> str:
        return f"TokenPair(expires_in={self.expires_in})"
