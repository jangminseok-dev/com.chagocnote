from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.token_dto import AccessToken


class TokenIssuerPort(ABC):
    @abstractmethod
    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False,
        ttl_seconds: int | None = None,
    ) -> AccessToken:
        """fresh_login 이면 발급 시각을 auth_time 으로 찍는다(소셜 로그인).
        auth_time 을 주면 그 값을 그대로 물려준다(수단 해제). 둘 다 없으면 찍지 않는다(갱신).
        ttl_seconds 를 주면 기본 수명 대신 그 수명으로 발급한다(보호자 웹 세션)."""
