from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_sales_visits_dto import ListSalesVisitsQuery, SalesVisitsView


class ListSalesVisitsUseCase(ABC):
    @abstractmethod
    async def list_sales_visits(self, query: ListSalesVisitsQuery) -> SalesVisitsView: ...
