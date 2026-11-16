from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.guardian_report_dto import GuardianMediaPageView, ListGuardianMediaQuery


class ListGuardianMediaUseCase(ABC):
    @abstractmethod
    async def list_media(self, query: ListGuardianMediaQuery) -> GuardianMediaPageView: ...
