from __future__ import annotations

from abc import ABC, abstractmethod

from search.app.dtos.search_records_dto import SearchRecordsQuery, SearchResultView


class SearchRecordsUseCase(ABC):
    @abstractmethod
    async def search_records(self, query: SearchRecordsQuery) -> SearchResultView: ...
