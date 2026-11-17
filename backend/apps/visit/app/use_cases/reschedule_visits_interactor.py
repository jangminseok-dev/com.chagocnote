from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.visit_events import VisitRescheduled
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.series_scope import FOLLOWING, ensure_free, lock_scope, notice_parts
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.send_bundle import SERIES_CHANGE
from visit.domain.services.visit_schedule import check_same_day, check_start
from visit.domain.services.visit_series import earliest_ids, move_order, wall_delta, wall_shift


class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
    def __init__(
        self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
        schedule: ScheduleRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
        now: Callable[[], datetime], *, shops: ShopProfilePort,
    ) -> None:
        self._visits = visits
        self._board = board
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._events = events
        self._now = now
        self._shops = shops

    async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        check_start(command.starts_at, now, tz)
        scope = await lock_scope(
            ctx, command.visit_ids, following=command.scope == FOLLOWING, family=command.family,
            skip_ids=frozenset(command.skip_visit_ids), visits=self._visits, directory=self._directory)
        locked = scope.anchors
        if any(v.status != RESERVED for v in locked):
            raise VisitStateConflictError("예약됨인 방문만 옮길 수 있습니다.")
        longest = max(v.duration_minutes for v in locked)
        check_same_day(command.starts_at, longest, tz)
        if scope.series_id is None:
            moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
            nearest = frozenset(v.id for v in moved)
        else:
            # 이후 전부(⑭) — 이 회차가 움직인 벽시계 차이만큼 뒤의 예약됨을 모두 민다. 걸린 회차가 있으면 쓰기 전에 409.
            delta = wall_delta(locked[0].starts_at, command.starts_at, tz)
            moves = [(v, wall_shift(v.starts_at, delta, tz)) for v in scope.targets]
            for visit, new in moves:
                check_same_day(new, visit.duration_minutes, tz)
            await ensure_free(ctx, moves, self._visits, now)
            moved = await self._visits.move_each(ctx, [(v.id, new) for v, new in move_order(moves)])
            nearest = earliest_ids(scope.targets)
        previous = {v.id: v.starts_at for v in scope.targets}
        for visit in moved:
            # 가족 묶음은 같은 새 시각의 아이들. 이후 전부의 나머지 회차는 조용히(변경 안내 없이 리마인드만, P12).
            family = tuple(sorted(v.pet_id for v in moved if v.starts_at == visit.starts_at and v.pet_id is not None))
            await self._events.publish(VisitRescheduled(
                ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                starts_at=visit.starts_at, occurred_at=now, previous_starts_at=previous[visit.id],
                quiet=visit.id not in nearest, family_pet_ids=family))
        for visit in moved:   # 검색 문서의 날짜를 새 방문 날로(⑨) — 방문마다
            await self._events.publish(SearchSourceChanged(ctx=ctx, scope="visit", ref_id=visit.id))
        settings = await self._schedule.ensure(ctx)
        warnings = await warnings_after_save(
            ctx, locked[0].customer_id, command.starts_at, longest, settings, self._board, self._schedule
        )
        views = await describe_visits(ctx, moved, self._directory, self._menus)
        notice = [] if scope.series_id is None else await notice_parts(ctx, SERIES_CHANGE, views, self._shops)
        return RescheduledVisitsView(visits=views, warnings=warnings, notice=notice)
