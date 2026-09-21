from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery, TenancyMyselfResponse


class TenancyMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: TenancyMyselfQuery) -> TenancyMyselfResponse: ...
