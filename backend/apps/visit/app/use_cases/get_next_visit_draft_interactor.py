from __future__ import annotations

from zoneinfo import ZoneInfo

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, NextVisitDraftView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.domain.entities.visit import CANCELED, COMPLETED, NO_SHOW
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_cycle import interval_weeks, next_start


class GetNextVisitDraftInteractor(GetNextVisitDraftUseCase):
    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, menus: MenuRepository
    ) -> None:
        self._visits = visits
        self._history = history
        self._menus = menus

    async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        # 취소·노쇼한 방문에는 다음이 없다. 완료 전(예약됨·미용 중)이라도 초안은 준다 — 완료 시트가
        # 누르기 전에 "언제로 잡히는지"를 보여야 해서다(③-A2).
        if visit.status in (CANCELED, NO_SHOW):
            raise VisitStateConflictError("취소·노쇼한 방문에서는 다음 예약을 잡을 수 없습니다.")
        group = [v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.status not in (CANCELED, NO_SHOW)]
        starts = await self._history.completed_starts(ctx, visit.customer_id, visit.pet_id, limit=2)
        if visit.status != COMPLETED:
            # 아직 완료 전이면 이 방문을 "이번"으로 놓고 직전 완료 방문과의 간격을 본다.
            starts = [visit.starts_at, *[s for s in starts if s < visit.starts_at][:1]]
        weeks = interval_weeks(starts)
        active = {m.id: m for m in await self._menus.list_active_by_ids(ctx, list(visit.menu_ids))}
        return NextVisitDraftView(
            customer_id=visit.customer_id,
            pet_ids=sorted(v.pet_id for v in group if v.pet_id is not None),
            starts_at=next_start(visit.starts_at, weeks, ctx.timezone).astimezone(ZoneInfo(ctx.timezone)),
            duration_minutes=visit.duration_minutes,
            menus=[MenuBriefView(menu_id=m, name=active[m].name) for m in visit.menu_ids if m in active],
            interval_weeks=weeks,
        )
