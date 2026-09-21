from __future__ import annotations

from abc import ABC, abstractmethod

from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery, PlatformMyselfResponse


class PlatformMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: PlatformMyselfQuery) -> PlatformMyselfResponse: ...
