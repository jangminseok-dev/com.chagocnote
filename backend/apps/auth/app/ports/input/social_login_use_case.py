from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.social_login_dto import SocialLoginCommand, SocialLoginResult


class SocialLoginUseCase(ABC):
    @abstractmethod
    async def login(self, command: SocialLoginCommand) -> SocialLoginResult: ...
