from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.list_day_visits_dto import (
    DayCountsView,
    DayVisitItemView,
    DayVisitsView,
    ListDayVisitsQuery,
)
from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.cover_reader import cover_urls
from visit.app.services.visit_reader import describe_visits
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_board import is_unresolved, overlaps_other_group, status_counts
from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date


class ListDayVisitsInteractor(ListDayVisitsUseCase):
    """하루 화면 — 그날 시작하는 방문 전부(취소·노쇼 포함)를 시작 순으로."""

    def __init__(
        self, board: VisitBoardRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, records: VisitRecordRepository, library: MediaLibraryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._board = board
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._records = records
        self._library = library
        self._now = now

    async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView:
        ctx, tz, day = query.ctx, query.ctx.timezone, query.day
        if not (2000 <= day.year <= 2100):
            raise VisitInputError("날짜가 올바르지 않습니다.")
        settings = await self._schedule.ensure(ctx)
        start, end = day_bounds(day, tz)
        visits = await self._board.list_between(ctx, start, end)
        occupied = await self._board.list_occupied(ctx, start, end)   # 전날 밤에 시작한 방문도 겹칠 수 있다
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        today = local_date(self._now(), tz)
        views = await describe_visits(ctx, visits, self._directory, self._menus)
        recorded = await self._records.list_many(ctx, [v.id for v in visits])
        covers = await cover_urls(ctx, recorded, self._library)
        items = [
            DayVisitItemView(
                visit=view,
                group_key=f"{visit.customer_id}:{visit.starts_at.isoformat()}",
                overlapping=overlaps_other_group(visit, occupied),
                unresolved=is_unresolved(visit, today, tz),
                has_record=visit.id in recorded,
                cover=covers.get(visit.id),
            )
            for visit, view in zip(visits, views)
        ]
        return DayVisitsView(
            date=day,
            closed_day=is_closed_day(day, settings, closed),
            counts=DayCountsView.of(status_counts(visits), unresolved=sum(item.unresolved for item in items)),
            items=items,
        )
