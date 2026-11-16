from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.get_visit_calendar_dto import (
    CalendarDayView,
    GetVisitCalendarQuery,
    VisitCalendarView,
)
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.services.cover_reader import cover_urls
from visit.app.services.remaining_work import anonymized_customers
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_board import COUNTED, is_unresolved
from visit.domain.services.visit_marks import is_report_unsent, is_unpaid
from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date

COVERS_PER_DAY = 4   # 미리보기 카드에 겹쳐 보이는 썸네일 수


class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
    """월 달력 — 날마다 마릿수·완료·예약·정리 안 됨, 휴무, 대표 사진. 위쪽 '정리 안 된 예약 N건'은 매장 전체다."""

    def __init__(
        self, board: VisitBoardRepository, schedule: ScheduleRepository, records: VisitRecordRepository,
        library: MediaLibraryPort, now: Callable[[], datetime], reports: ReportRepository,
        revisit_settings: RevisitSettingsRepository, directory: CustomerDirectoryPort,
    ) -> None:
        self._directory = directory
        self._reports = reports
        self._revisit_settings = revisit_settings
        self._board = board
        self._schedule = schedule
        self._records = records
        self._library = library
        self._now = now

    async def get_visit_calendar(self, query: GetVisitCalendarQuery) -> VisitCalendarView:
        ctx, tz = query.ctx, query.ctx.timezone
        if not (1 <= query.month <= 12 and 2000 <= query.year <= 2100):
            raise VisitInputError("달이 올바르지 않습니다.")
        settings = await self._schedule.ensure(ctx)
        last = calendar.monthrange(query.year, query.month)[1]
        first_day, last_day = date(query.year, query.month, 1), date(query.year, query.month, last)
        start, _ = day_bounds(first_day, tz)
        _, end = day_bounds(last_day, tz)
        today = local_date(self._now(), tz)

        by_day = defaultdict(list)
        month_visits = await self._board.list_between(ctx, start, end)   # 시작 순
        for visit in month_visits:
            by_day[local_date(visit.starts_at, tz)].append(visit)
        completed_ids = [v.id for v in month_visits if v.status == COMPLETED]
        recorded = await self._records.list_many(ctx, completed_ids)
        covers = await cover_urls(ctx, recorded, self._library)
        # 남은 일(⑬) — 완료 방문의 것이고 지난 날·오늘만이다. 익명화한 고객의 방문은 끝낼 수 없으니 세지 않는다(하루
        # 마무리와 같은 범위). 알림장 줄과 고객은 그달의 완료 방문에 대해 한 번씩 읽는다.
        ever = await self._reports.visit_ids_with_report(ctx, completed_ids) if completed_ids else set()
        gone = await anonymized_customers(ctx, [v for v in month_visits if v.status == COMPLETED], self._directory)
        count_unsent = (await self._revisit_settings.get(ctx)).count_unsent_reports
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, first_day, last_day))
        days = []
        for number in range(1, last + 1):
            day = date(query.year, query.month, number)
            visits = by_day[day]
            day_covers = [covers[v.id] for v in visits if v.id in covers]   # 완료 방문만 covers 에 있다
            workable = [v for v in visits if v.customer_id not in gone] if day <= today else []
            days.append(CalendarDayView(
                date=day,
                visit_count=sum(v.status in COUNTED for v in visits),
                completed_count=sum(v.status == COMPLETED for v in visits),
                open_count=sum(v.is_active for v in visits),
                unresolved_count=sum(is_unresolved(v, today, tz) for v in visits),
                unpaid_count=sum(is_unpaid(v, recorded.get(v.id)) for v in workable),
                report_unsent_count=sum(
                    is_report_unsent(v, recorded.get(v.id), ever_sent=v.id in ever, count=count_unsent)
                    for v in workable),
                closed_day=is_closed_day(day, settings, closed),
                cover=day_covers[0] if day_covers else None,
                covers=day_covers[:COVERS_PER_DAY],
            ))
        today_start, _ = day_bounds(today, tz)
        total, oldest = await self._board.unresolved_before(ctx, today_start)
        return VisitCalendarView(
            year=query.year, month=query.month, days=days, unresolved_total=total,
            oldest_unresolved_date=local_date(oldest, tz) if oldest else None,
        )
