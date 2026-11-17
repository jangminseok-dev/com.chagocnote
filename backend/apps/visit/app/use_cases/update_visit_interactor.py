from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.visit_events import VisitRescheduled
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.series_scope import FOLLOWING, ensure_free, lock_scope, notice_parts
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED, Visit
from visit.domain.errors import MenuNotAvailableError, VisitInputError, VisitStateConflictError
from visit.domain.services.send_bundle import SERIES_CHANGE
from visit.domain.services.visit_schedule import check_duration, check_same_day, check_start
from visit.domain.services.visit_series import earliest_ids, move_order, wall_delta, wall_shift


class UpdateVisitInteractor(UpdateVisitUseCase):
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

    async def update_visit(self, command: UpdateVisitCommand) -> UpdatedVisitView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        check_duration(command.duration_minutes)
        # 새로 고른 아이만 가족 확인에 넘긴다(같은 보호자의 아이인지, 무지개다리가 아닌지 — V13).
        # 그대로인 아이는 넘기지 않는다 — 완료한 방문의 아이가 나중에 무지개다리를 건넜어도 메모는 고친다.
        before = await self._visits.get(ctx, command.visit_id)
        if command.scope == FOLLOWING and before.series_id is not None:
            return await self._update_following(command, before)
        changed_pet = command.pet_id is not None and command.pet_id != before.pet_id
        new_pet = (command.pet_id,) if changed_pet else ()
        [current] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory, new_pet)
        if current.pet_id != before.pet_id:
            raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")

        moved = command.starts_at != current.starts_at or command.pet_id != current.pet_id
        if moved and current.status != RESERVED:
            raise VisitStateConflictError("날짜·시간·반려동물은 예약됨일 때만 바꿀 수 있습니다.")
        if command.starts_at != current.starts_at:
            check_start(command.starts_at, now, tz)
        check_same_day(command.starts_at, command.duration_minutes, tz)
        # 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다(완료한 방문의 메모만 고치는 경우).
        chosen = set(command.menu_ids)
        allowed = {m.id for m in await self._menus.list_active_by_ids(ctx, list(chosen))} | set(current.menu_ids)
        if not chosen <= allowed:
            raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")

        updated = await self._visits.update_details(
            ctx, current.id, command.starts_at, command.pet_id, command.duration_minutes, command.menu_ids,
            command.memo,
        )
        # 시각이 바뀌었을 때만 알린다 — 반려동물·메뉴·메모만 바뀐 것은 보호자에게 알릴 일이 아니다.
        if updated.starts_at != current.starts_at:
            await self._events.publish(VisitRescheduled(
                ctx=ctx, visit_id=updated.id, customer_id=updated.customer_id, pet_id=updated.pet_id,
                starts_at=updated.starts_at, occurred_at=now, previous_starts_at=current.starts_at,
                family_pet_ids=(updated.pet_id,) if updated.pet_id is not None else ()))
        # 예약 메모와 방문 날짜가 검색에 든다(⑨) — 시각이 그대로여도 알린다.
        await self._events.publish(SearchSourceChanged(ctx=ctx, scope="visit", ref_id=updated.id))
        warnings = []
        if updated.is_active:
            settings = await self._schedule.ensure(ctx)
            warnings = await warnings_after_save(
                ctx, updated.customer_id, updated.starts_at, updated.duration_minutes, settings, self._board,
                self._schedule,
            )
        [view] = await describe_visits(ctx, [updated], self._directory, self._menus)
        return UpdatedVisitView(visit=view, warnings=warnings)

    async def _update_following(self, command: UpdateVisitCommand, before: Visit) -> UpdatedVisitView:
        """이후 전부 고치기(⑭ 설계 3.7) — 메뉴·소요·메모를 같게 하고, 시각이 바뀌었으면 같은 벽시계 차이만큼 민다.
        아이 바꾸기는 이 예약만이다. 걸린 회차가 있으면 아무것도 쓰기 전에 409."""
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        if command.pet_id != before.pet_id:
            raise VisitInputError("아이를 바꾸는 것은 이 예약만 할 수 있어요.")
        scope = await lock_scope(
            ctx, [command.visit_id], following=True, family=command.family,
            skip_ids=frozenset(command.skip_visit_ids), visits=self._visits, directory=self._directory)
        [anchor] = scope.anchors
        if anchor.status != RESERVED:
            raise VisitStateConflictError("이후 전부는 예약됨인 예약에서만 바꿀 수 있어요.")
        if command.starts_at != anchor.starts_at:
            check_start(command.starts_at, now, tz)
        chosen = set(command.menu_ids)
        allowed = {m.id for m in await self._menus.list_active_by_ids(ctx, list(chosen))} | set(anchor.menu_ids)
        if not chosen <= allowed:
            raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")
        delta = wall_delta(anchor.starts_at, command.starts_at, tz)
        moves = [(v, wall_shift(v.starts_at, delta, tz)) for v in scope.targets]
        for _, new in moves:
            check_same_day(new, command.duration_minutes, tz)
        if delta:
            await ensure_free(ctx, moves, self._visits, now)
        updated = [
            await self._visits.update_details(ctx, v.id, new, v.pet_id, command.duration_minutes, command.menu_ids,
                                              command.memo)
            for v, new in move_order(moves)
        ]
        if delta:
            nearest = earliest_ids(scope.targets)
            previous = {v.id: v.starts_at for v in scope.targets}
            for visit in updated:   # 옮긴 차례대로 — 다음 회차의 옛 자리의 알림 줄을 지우지 않게(옮기기와 같다)
                family = tuple(sorted(v.pet_id for v in updated
                                      if v.starts_at == visit.starts_at and v.pet_id is not None))
                await self._events.publish(VisitRescheduled(
                    ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                    starts_at=visit.starts_at, occurred_at=now, previous_starts_at=previous[visit.id],
                    quiet=visit.id not in nearest, family_pet_ids=family))
        for visit in updated:   # 예약 메모와 방문 날짜가 검색에 든다(⑨) — 방문마다
            await self._events.publish(SearchSourceChanged(ctx=ctx, scope="visit", ref_id=visit.id))
        current = await self._visits.get(ctx, anchor.id)
        settings = await self._schedule.ensure(ctx)
        warnings = await warnings_after_save(
            ctx, current.customer_id, current.starts_at, current.duration_minutes, settings, self._board,
            self._schedule,
        )
        [view] = await describe_visits(ctx, [current], self._directory, self._menus)
        notice = []
        if delta:
            notice = await notice_parts(
                ctx, SERIES_CHANGE, await describe_visits(ctx, updated, self._directory, self._menus), self._shops)
        return UpdatedVisitView(visit=view, warnings=warnings, notice=notice)
