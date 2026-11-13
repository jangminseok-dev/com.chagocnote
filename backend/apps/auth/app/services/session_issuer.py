from __future__ import annotations

from auth.app.dtos.token_dto import TokenPair
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.token_issuer_port import TokenIssuerPort
from auth.domain.services.refresh_token_factory import new_refresh_token
from core.config import WEB_ACCESS_TOKEN_TTL_SECONDS


class SessionIssuer:
    """로그인과 토큰 갱신이 함께 쓰는 발급 절차."""

    def __init__(self, token_issuer: TokenIssuerPort, refresh_store: RefreshTokenStorePort) -> None:
        self._token_issuer = token_issuer
        self._refresh_store = refresh_store

    async def issue(
        self,
        user_id: int,
        generation: int | None = None,
        *,
        auth_time: int | None = None,
        fresh_login: bool = False,
    ) -> TokenPair:
        """generation 이 없으면 현재 세대로 발급한다(로그인). 갱신은 꺼낼 때 받은 세대를 넘긴다 —
        그 사이 모든 세션 폐기가 끼어들었다면 새 토큰도 함께 무효가 되어야 하기 때문이다.
        fresh_login 은 소셜 로그인만 켠다. auth_time 은 수단 해제가 요청 토큰의 값을 물려줄 때만 쓴다."""
        access = self._token_issuer.issue_access(
            user_id, auth_time=auth_time, fresh_login=fresh_login
        )
        refresh = new_refresh_token(user_id)
        if generation is None:
            generation = await self._refresh_store.current_generation(user_id)
        await self._refresh_store.save(refresh, user_id, generation)
        return TokenPair(
            access_token=access.token, refresh_token=refresh, expires_in=access.expires_in
        )

    async def issue_web(self, user_id: int) -> TokenPair:
        """보호자 웹 세션 — 30분짜리 액세스 토큰 하나만 내준다. 리프레시 토큰을 만들지도 저장하지도 않는다.

        웹은 탭 둘·뒤로 가기로 갱신이 겹치기 쉽고, 재사용이 감지되면 그 계정의 모든 세션(매장 앱 포함)이 끊긴다.
        그래서 웹에는 갱신할 것을 주지 않는다 — 30분이 지나면 다시 로그인한다(⑦ 설계 4.4).
        계정을 바꾸는 일은 매장 앱에서 한다."""
        # 로그인 시각(auth_time)을 찍지 않는다 — 웹 세션은 '최근 로그인'이 필요한 일(탈퇴·수단 연결·해제)을 하지
        # 못한다. 수단 해제는 30일짜리 토큰 쌍을 새로 내주므로, 찍으면 그 길로 리프레시 토큰이 웹에 나간다.
        access = self._token_issuer.issue_access(user_id, ttl_seconds=WEB_ACCESS_TOKEN_TTL_SECONDS)
        return TokenPair(access_token=access.token, refresh_token=None, expires_in=access.expires_in)
