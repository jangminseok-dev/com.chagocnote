from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True, repr=False)
class IdentityRevocation:
    """제공자 쪽 연결을 끊는 데 필요한 것. DB 에서 신원을 지우기 전에 읽어 두고, 커밋 뒤에 쓴다.

    provider_refresh_token 은 복호화된 원문이다. 로그에 찍히지 않게 repr 을 막아 둔다.
    """

    provider: Provider
    provider_user_id: str
    provider_refresh_token: str | None

    def __repr__(self) -> str:
        return f"IdentityRevocation(provider={self.provider.value}, provider_user_id={self.provider_user_id})"
