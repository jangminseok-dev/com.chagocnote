from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.visit_events import VisitReserved
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.dtos.register_visit_dto import (
    RegisteredSeriesView,
    RegisteredVisitsView,
    RegisterVisitCommand,
    SeriesOccurrenceView,
)
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_series_repository import VisitSeriesRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.booking_inputs import chosen_duration
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import IN_PROGRESS, RESERVED
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_schedule import check_same_day, check_start, floor_to_step
from visit.domain.services.visit_series import MIN_COUNT, plan_occurrences
from visit.domain.value_objects.new_visit import NewVisit


class RegisterVisitInteractor(RegisterVisitUseCase):
    def __init__(
        self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
        schedule: ScheduleRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
        now: Callable[[], datetime], *, series: VisitSeriesRepository,
    ) -> None:
        self._visits = visits
        self._board = board
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._events = events
        self._now = now
        self._series = series

    async def register_visit(self, command: RegisterVisitCommand) -> RegisteredVisitsView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        if command.walk_in == (command.starts_at is not None):
            raise VisitInputError("예약 시각과 '지금 시작' 중 하나만 보내 주세요.")
        if command.walk_in and command.repeat is not None:
            raise VisitInputError("지금 시작한 손님에게는 반복을 걸 수 없어요.")
        settings = await self._schedule.ensure(ctx)
        duration = await chosen_duration(ctx, command.menu_ids, command.duration_minutes, self._menus, settings)
        if command.walk_in:
            starts_at, status, started_at = floor_to_step(now, tz), IN_PROGRESS, now
        else:
            starts_at, status, started_at = command.starts_at, RESERVED, None
            check_start(starts_at, now, tz)
        check_same_day(starts_at, duration, tz)
        starts = [starts_at]
        repeat = command.repeat
        if repeat is not None:
            # 회차는 같은 요일·같은 벽시계 시각. 1년 범위 밖은 미리 보기처럼 조용히 빠지고, 뺀 회차는 넣지 않는다(⑭ 3.7).
            kept, _ = plan_occurrences(starts_at, repeat.interval_weeks, repeat.count, tz, now)
            starts = [o.starts_at for o in kept if o.index not in set(repeat.skip)]
            if len(starts) < MIN_COUNT:
                raise VisitInputError("반복 예약은 두 번 이상이어야 해요.")

        # 고객 행 → 방문 행. 익명화·무지개다리·반려동물 삭제와 겹치지 않게 가족부터 잠근다(설계 4.2, V3).
        await self._directory.lock_family(ctx, command.customer_id, command.pet_ids)
        series = None
        if repeat is not None:
            series = await self._series.create(ctx, command.customer_id, repeat.interval_weeks, ctx.member_id)
        created = await self._visits.create_many(
            ctx,
            [
                NewVisit(customer_id=command.customer_id, pet_id=pet_id, starts_at=at,
                         duration_minutes=duration, status=status, started_at=started_at,
                         menu_ids=command.menu_ids, memo=command.memo, created_by_member_id=ctx.member_id,
                         series_id=None if series is None else series.id)
                for at in starts
                for pet_id in (command.pet_ids or (None,))
            ],
        )
        # 예약만 알린다 — '지금 시작'은 미용 중으로 시작하니 예약이 아니다. 같은 시각의 방문이 가족 묶음이다.
        # 반복이면 접수 안내는 가장 이른 회차 한 통이고, 둘째 회차부터는 리마인드만(series_followup, ⑭ P12).
        if status == RESERVED:
            first = min(v.starts_at for v in created)
            for visit in created:
                family = tuple(sorted(v.pet_id for v in created
                                      if v.starts_at == visit.starts_at and v.pet_id is not None))
                await self._events.publish(VisitReserved(
                    ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                    starts_at=visit.starts_at, occurred_at=now, series_followup=visit.starts_at != first,
                    family_pet_ids=family))
        # 예약 메모가 검색에 든다(⑨) — 지금 시작한 손님도, 메모가 없어도 방문마다 알린다(문서가 될지는 색인기가 정한다).
        for visit in created:
            await self._events.publish(SearchSourceChanged(ctx=ctx, scope="visit", ref_id=visit.id))

        warnings = {
            at: await warnings_after_save(ctx, command.customer_id, at, duration, settings, self._board, self._schedule)
            for at in starts
        }
        zone = ZoneInfo(tz)
        return RegisteredVisitsView(
            visits=await describe_visits(ctx, created, self._directory, self._menus), warnings=warnings[starts[0]],
            series=None if series is None else RegisteredSeriesView(
                id=series.id, interval_weeks=series.interval_weeks,
                occurrences=[SeriesOccurrenceView(starts_at=at.astimezone(zone), warnings=warnings[at])
                             for at in starts]),
        )
