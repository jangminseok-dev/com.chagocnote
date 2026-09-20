from __future__ import annotations

from auth.app.dtos.token_dto import TokenPair
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.token_issuer_port import TokenIssuerPort
from auth.domain.services.refresh_token_factory import new_refresh_token


class SessionIssuer:
    """로그인과 토큰 갱신이 함께 쓰는 발급 절차."""

    def __init__(self, token_issuer: TokenIssuerPort, refresh_store: RefreshTokenStorePort) -> None:
        self._token_issuer = token_issuer
        self._refresh_store = refresh_store

    async def issue(self, user_id: int) -> TokenPair:
        access = self._token_issuer.issue_access(user_id)
        refresh = new_refresh_token()
        await self._refresh_store.save(refresh, user_id)
        return TokenPair(
            access_token=access.token, refresh_token=refresh, expires_in=access.expires_in
        )
