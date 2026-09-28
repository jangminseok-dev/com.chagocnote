from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.completion_effects import apply_completion_effects
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.domain.errors import VisitStateConflictError
from visit.domain.state.visit_state import pets_to_confirm, transition


class TransitionVisitsInteractor(TransitionVisitsUseCase):
    """잠그고 → 전이하고 → 후속 처리를 부른다. 어느 행동이 무엇을 확인하는지는 도메인(`visit_state`)이 정한다."""

    def __init__(
        self, visits: VisitWriteRepository, history: VisitHistoryRepository, menus: MenuRepository,
        reports: ReportRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._history = history
        self._menus = menus
        self._reports = reports
        self._directory = directory
        self._now = now

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
        return TransitionedVisitsView(
            visits=await describe_visits(ctx, changed, self._directory, self._menus)
        )
