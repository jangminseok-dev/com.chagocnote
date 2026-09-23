from __future__ import annotations

from zoneinfo import ZoneInfo

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, NextVisitDraftView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_cycle import interval_weeks, next_start


class GetNextVisitDraftInteractor(GetNextVisitDraftUseCase):
    def __init__(self, visits: VisitRepository, menus: MenuRepository) -> None:
        self._visits = visits
        self._menus = menus

    async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        if visit.status != COMPLETED:
            raise VisitStateConflictError("완료한 방문에서만 다음 예약을 잡을 수 있습니다.")
        group = [v for v in await self._visits.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.status == COMPLETED]
        starts = await self._visits.completed_starts(ctx, visit.customer_id, visit.pet_id, limit=2)
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
