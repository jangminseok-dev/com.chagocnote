from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from visit.app.dtos.preview_repeat_dto import OccurrenceView, PreviewRepeatQuery, RepeatPreviewView
from visit.app.ports.input.preview_repeat_use_case import PreviewRepeatUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.services.booking_inputs import chosen_duration
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.services.visit_schedule import check_same_day, check_start
from visit.domain.services.visit_series import plan_occurrences


class PreviewRepeatInteractor(PreviewRepeatUseCase):
    """반복 회차 미리 보기(⑭ 설계 3.7) — 회차마다 시각과 경고(휴무·겹침, 막지 않는다), 그 아이에게 이미 예약이 있는
    자리. 예약 가능 범위(1년)를 넘는 회차는 목록에 없고 그 수를 준다. 아무것도 저장하지 않는다."""

    def __init__(
        self, visits: VisitLookupRepository, board: VisitBoardRepository, menus: MenuRepository,
        schedule: ScheduleRepository, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._board = board
        self._menus = menus
        self._schedule = schedule
        self._now = now

    async def preview_repeat(self, query: PreviewRepeatQuery) -> RepeatPreviewView:
        ctx, tz, now = query.ctx, query.ctx.timezone, self._now()
        check_start(query.starts_at, now, tz)
        settings = await self._schedule.ensure(ctx)
        duration = await chosen_duration(ctx, query.menu_ids, query.duration_minutes, self._menus, settings)
        check_same_day(query.starts_at, duration, tz)
        kept, beyond = plan_occurrences(query.starts_at, query.interval_weeks, query.count, tz, now)
        pets = set(query.pet_ids) or {None}
        taken = {v.starts_at for v in await self._visits.active_at(ctx, query.customer_id, [o.starts_at for o in kept])
                 if v.pet_id in pets}
        zone = ZoneInfo(tz)
        occurrences = [
            OccurrenceView(
                index=o.index, starts_at=o.starts_at.astimezone(zone),
                warnings=await warnings_after_save(ctx, query.customer_id, o.starts_at, duration, settings,
                                                   self._board, self._schedule),
                taken=o.starts_at in taken)
            for o in kept
        ]
        return RepeatPreviewView(interval_weeks=query.interval_weeks, count=query.count, occurrences=occurrences,
                                 beyond_horizon=beyond)
