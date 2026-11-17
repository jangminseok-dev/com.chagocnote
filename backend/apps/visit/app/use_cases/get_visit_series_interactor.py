from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.get_visit_series_dto import GetVisitSeriesQuery, VisitSeriesView
from visit.app.ports.input.get_visit_series_use_case import GetVisitSeriesUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_series_repository import VisitSeriesRepository
from visit.app.services.visit_reader import describe_visits


class GetVisitSeriesInteractor(GetVisitSeriesUseCase):
    """반복 묶음의 예약 목록(⑭) — 상태와 상관없이 시각 순. 다른 매장의 묶음이면 VISIT_SERIES_NOT_FOUND."""

    def __init__(
        self, visits: VisitLookupRepository, series: VisitSeriesRepository, directory: CustomerDirectoryPort,
        menus: MenuRepository,
    ) -> None:
        self._visits = visits
        self._series = series
        self._directory = directory
        self._menus = menus

    async def get_visit_series(self, query: GetVisitSeriesQuery) -> VisitSeriesView:
        ctx = query.ctx
        series = await self._series.get(ctx, query.series_id)
        visits = await self._visits.list_series(ctx, series.id)
        return VisitSeriesView(id=series.id, interval_weeks=series.interval_weeks,
                               visits=await describe_visits(ctx, visits, self._directory, self._menus))
