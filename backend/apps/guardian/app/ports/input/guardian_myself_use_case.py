from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.guardian_myself_dto import GuardianMyselfQuery, GuardianMyselfResponse


class GuardianMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: GuardianMyselfQuery) -> GuardianMyselfResponse: ...
