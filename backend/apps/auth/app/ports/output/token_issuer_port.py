from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.token_dto import AccessToken


class TokenIssuerPort(ABC):
    @abstractmethod
    def issue_access(self, user_id: int) -> AccessToken: ...
