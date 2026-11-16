from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.visit_events import VisitCanceled, VisitClosed, VisitEvent, VisitReserved
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.completion_effects import apply_completion_effects
from visit.app.services.revisit import pet_cycles
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import Visit
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_cycle import COMPUTED, MANUAL, NONE
from visit.domain.services.visit_schedule import local_date
from visit.domain.state.visit_state import pets_to_confirm, transition


class TransitionVisitsInteractor(TransitionVisitsUseCase):
    """잠그고 → 전이하고 → 후속 처리를 부르고 → 이벤트를 발행한다. 어느 행동이 무엇을 확인하는지는 도메인(`visit_state`)이 정한다."""

    def __init__(
        self, visits: VisitWriteRepository, history: VisitHistoryRepository, menus: MenuRepository,
        reports: ReportRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
        now: Callable[[], datetime], settings: RevisitSettingsRepository,
    ) -> None:
        self._visits = visits
        self._history = history
        self._menus = menus
        self._reports = reports
        self._directory = directory
        self._events = events
        self._now = now
        self._settings = settings

    async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView:
        ctx, ids = command.ctx, list(command.visit_ids)
        # 시간을 다시 차지하는 행동(되돌리기)만 그 아이가 무지개다리를 건넜는지 가족 확인을 거친다(V7).
        pet_ids = pets_to_confirm(command.action, await self._visits.get_many(ctx, ids))
        locked = await lock_visits(ctx, ids, self._visits, self._directory, pet_ids)
        # 가족 확인은 잠그기 전 반려동물로 판단했다 — 잠근 뒤 다시 본 값이 다르면(그 사이 다른 요청이 반려동물을
        # 바꿨을 수 있다) 낡은 확인이라 다시 불러오게 한다.
        if pets_to_confirm(command.action, locked) != pet_ids:
            raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")

        now = self._now()
        # 알림장을 보냈는지도 잠근 뒤에 읽는다 — 보내기가 같은 잠금을 쥐므로 판정과 쓰기 사이에 링크가 생기지 않는다.
        sent = await self._reports.live_visit_ids(ctx, ids, now)
        locked = [replace(v, has_live_report=v.id in sent) for v in locked]
        # 잠근 뒤 다시 읽은 상태로 모두 판정한 다음에 쓴다 — 하나라도 안 되면 아무것도 바꾸지 않는다.
        changes = [(v.id, transition(v, command.action, now, ctx.timezone, command.cancel_reason)) for v in locked]
        changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)
        await apply_completion_effects(ctx, locked, changed, self._history, self._directory)
        # 쓰기가 다 끝난 뒤에 알린다 — 구독자가 던지면 전이도 함께 롤백된다(설계 5.1, N13).
        # 가족 묶음은 같은 보호자(잠금이 보장)·같은 시작 시각인 것끼리다.
        for visit in changed:
            family = tuple(sorted(v.pet_id for v in changed if v.starts_at == visit.starts_at and v.pet_id is not None))
            event = await self._event_for(ctx, command.action, command.cancel_reason, visit, now, family)
            if event is not None:
                await self._events.publish(event)
        return TransitionedVisitsView(
            visits=await describe_visits(ctx, changed, self._directory, self._menus)
        )

    async def _cycle_of(self, ctx: ShopContext, pet_id: int | None, now: datetime) -> dict:
        """다음 예약 제안의 주 수에 쓸 아이의 주기(⑬ 설계 3.4) — 이번 완료까지 넣어 계산한다(이미 완료로 썼다).
        cycle_weeks 는 직접 정한 값·계산한 값일 때만 싣는다(간격 하나는 주기가 아니다)."""
        settings = await self._settings.get(ctx)
        if pet_id is None:
            return dict(cycle_source=NONE, default_cycle_weeks=settings.default_cycle_weeks)
        facts = await self._directory.revisit_facts(ctx, (pet_id,))
        manual = {pet_id: facts[pet_id].grooming_cycle_weeks} if pet_id in facts else {}
        cycle = (await pet_cycles(ctx, [pet_id], manual, self._history, settings,
                                  local_date(now, ctx.timezone)))[pet_id]
        known = cycle.source in (MANUAL, COMPUTED)
        return dict(cycle_weeks=cycle.weeks if known else None, cycle_source=cycle.source,
                    default_cycle_weeks=settings.default_cycle_weeks)

    async def _event_for(
        self, ctx: ShopContext, action: str, cancel_reason: str | None, visit: Visit, now: datetime,
        family: tuple[int, ...],
    ) -> VisitEvent | None:
        """행동마다 알릴 사실. 시작은 알릴 것이 없다. 되돌리기의 결과는 늘 예약됨이다(`VisitState.revert`)."""
        common = dict(ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                      starts_at=visit.starts_at, occurred_at=now, family_pet_ids=family)
        if action == "cancel":
            return VisitCanceled(**common, reason=cancel_reason)
        if action == "complete":
            previous = await self._history.latest_completed_start_excluding(
                ctx, visit.customer_id, visit.pet_id, visit.id)
            return VisitClosed(**common, outcome="completed", previous_completed_at=previous,
                               **await self._cycle_of(ctx, visit.pet_id, now))
        if action == "no_show":
            return VisitClosed(**common, outcome="no_show", previous_completed_at=None)
        if action == "revert":
            return VisitReserved(**common, revived=True)
        return None
