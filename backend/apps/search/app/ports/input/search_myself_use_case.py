from __future__ import annotations

from abc import ABC, abstractmethod

from search.app.dtos.search_myself_dto import SearchMyselfQuery, SearchMyselfResponse


class SearchMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: SearchMyselfQuery) -> SearchMyselfResponse: ...
