from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_sales_summary_dto import GetSalesSummaryQuery, SalesSummaryView


class GetSalesSummaryUseCase(ABC):
    @abstractmethod
    async def get_sales_summary(self, query: GetSalesSummaryQuery) -> SalesSummaryView: ...
