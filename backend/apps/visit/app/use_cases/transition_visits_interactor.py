from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitStateConflictError
from visit.domain.state.visit_state import transition


class TransitionVisitsInteractor(TransitionVisitsUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._directory = directory
        self._now = now

    async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView:
        ctx = command.ctx
        # 되돌리기는 끝난 방문을 다시 시간을 차지하는 예약으로 만든다 — 그 아이가 무지개다리를 건넜으면
        # 가족 확인이 막는다(V7). 다른 행동은 새로 시간을 차지하지 않아 보호자만 잠근다.
        pet_ids: tuple[int, ...] = ()
        if command.action == "revert":
            pet_ids = tuple(sorted({
                v.pet_id for v in await self._visits.get_many(ctx, list(command.visit_ids)) if v.pet_id is not None
            }))
        locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory, pet_ids)
        # 가족 확인은 잠그기 전 반려동물로 판단했다 — 잠근 뒤 다시 본 값이 다르면(그 사이 다른 요청이 반려동물을
        # 바꿨을 수 있다) 낡은 확인이라 다시 불러오게 한다.
        if command.action == "revert" and {v.pet_id for v in locked if v.pet_id is not None} != set(pet_ids):
            raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")

        now = self._now()
        # 잠근 뒤 다시 읽은 상태로 모두 판정한 다음에 쓴다 — 하나라도 안 되면 아무것도 바꾸지 않는다.
        changes = [(v.id, transition(v, command.action, now, ctx.timezone, command.cancel_reason)) for v in locked]
        changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)

        if any(v.status == COMPLETED for v in locked) or any(c.status == COMPLETED for _, c in changes):
            customer_id = locked[0].customer_id
            latest = await self._visits.latest_completed_start(ctx, customer_id)
            await self._directory.set_last_visit(ctx, customer_id, latest)
        return TransitionedVisitsView(
            visits=await describe_visits(ctx, changed, self._directory, self._menus)
        )
