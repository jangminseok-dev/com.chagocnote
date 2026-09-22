from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.token_dto import AccessToken


class TokenIssuerPort(ABC):
    @abstractmethod
    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False
    ) -> AccessToken:
        """fresh_login 이면 발급 시각을 auth_time 으로 찍는다(소셜 로그인).
        auth_time 을 주면 그 값을 그대로 물려준다(수단 해제). 둘 다 없으면 찍지 않는다(갱신)."""
