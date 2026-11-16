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
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_check_repository import VisitCheckRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.cover_reader import cover_urls
from visit.app.services.visit_checks import CheckTarget, read_checks
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_checks import COUNTED, CUSTOMER, PET
from visit.domain.services.visit_board import is_unresolved, overlaps_other_group, status_counts
from visit.domain.services.visit_marks import is_report_unsent, is_unpaid, marks_of
from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date


class ListDayVisitsInteractor(ListDayVisitsUseCase):
    """하루 화면 — 그날 시작하는 방문 전부(취소·노쇼 포함)를 시작 순으로."""

    def __init__(
        self, board: VisitBoardRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, records: VisitRecordRepository, library: MediaLibraryPort,
        reports: ReportRepository, now: Callable[[], datetime], checks: VisitCheckRepository,
        revisit_settings: RevisitSettingsRepository,
    ) -> None:
        self._revisit_settings = revisit_settings
        self._board = board
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._records = records
        self._library = library
        self._reports = reports
        self._now = now
        self._checks = checks

    async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView:
        ctx, tz, day = query.ctx, query.ctx.timezone, query.day
        if not (2000 <= day.year <= 2100):
            raise VisitInputError("날짜가 올바르지 않습니다.")
        settings = await self._schedule.ensure(ctx)
        start, end = day_bounds(day, tz)
        visits = await self._board.list_between(ctx, start, end)
        occupied = await self._board.list_occupied(ctx, start, end)   # 전날 밤에 시작한 방문도 겹칠 수 있다
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        now = self._now()
        today = local_date(now, tz)
        views = await describe_visits(ctx, visits, self._directory, self._menus)
        recorded = await self._records.list_many(ctx, [v.id for v in visits])
        covers = await cover_urls(ctx, recorded, self._library)
        sent = await self._reports.live_visit_ids(ctx, [v.id for v in visits], now)
        done_ids = [v.id for v in visits if v.status == COMPLETED]
        ever = await self._reports.visit_ids_with_report(ctx, done_ids) if done_ids else set()
        count_unsent = (await self._revisit_settings.get(ctx)).count_unsent_reports
        # 확인할 것은 살아 있는 방문에만 있다. 방문이 몇 개든 한 번에 읽는다.
        checks = (await read_checks(
            ctx,
            [
                CheckTarget(key=v.id, customer_id=v.customer_id, pet_id=v.pet_id, on=day, before=v.starts_at)
                for v in visits if v.status in ACTIVE_STATUSES
            ],
            self._directory, self._checks, today,
        )).by_key

        def counted(visit_id: int, scope: str) -> int:
            return sum(1 for c in checks.get(visit_id, ()) if c.code in COUNTED and c.scope == scope)

        items = [
            DayVisitItemView(
                visit=view,
                group_key=f"{visit.customer_id}:{visit.starts_at.isoformat()}",
                overlapping=overlaps_other_group(visit, occupied),
                unresolved=is_unresolved(visit, today, tz),
                has_record=visit.id in recorded,
                cover=covers.get(visit.id),
                report_sent=visit.id in sent,
                customer_check_count=counted(visit.id, CUSTOMER),
                pet_check_count=counted(visit.id, PET),
                marks=marks_of(visit, recorded.get(visit.id), visit.id in sent),
            )
            for visit, view in zip(visits, views)
        ]
        # 남은 일(⑬)은 지난 날·오늘만이고, 익명화한 고객의 방문은 끝낼 수 없으니 세지 않는다(하루 마무리와 같은 범위).
        workable = [v for v, view in zip(visits, views) if view.customer.name is not None] if day <= today else []
        unpaid = sum(is_unpaid(v, recorded.get(v.id)) for v in workable)
        unsent = sum(is_report_unsent(v, recorded.get(v.id), ever_sent=v.id in ever, count=count_unsent)
                     for v in workable)
        with_checks = sum(1 for i in items if i.customer_check_count + i.pet_check_count > 0)
        return DayVisitsView(
            date=day,
            closed_day=is_closed_day(day, settings, closed),
            counts=DayCountsView.of(status_counts(visits), unresolved=sum(item.unresolved for item in items),
                                    unpaid=unpaid, report_unsent=unsent, checks=with_checks),
            items=items,
        )
