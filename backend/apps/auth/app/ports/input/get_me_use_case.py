from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.get_me_dto import GetMeQuery, MeResponse


class GetMeUseCase(ABC):
    @abstractmethod
    async def get_me(self, query: GetMeQuery) -> MeResponse: ...
