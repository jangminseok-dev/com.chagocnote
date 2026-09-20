from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.auth_myself_dto import AuthMyselfQuery, AuthMyselfResponse


class AuthMyselfUseCase(ABC):
    """인증 (auth) 라우터 묶음의 자기소개."""

    @abstractmethod
    async def introduce_myself(self, query: AuthMyselfQuery) -> AuthMyselfResponse: ...
