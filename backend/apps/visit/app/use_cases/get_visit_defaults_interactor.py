from __future__ import annotations

from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery, VisitDefaultsView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository


class GetVisitDefaultsInteractor(GetVisitDefaultsUseCase):
    """다른 매장의 반려동물 ID 를 넣어도 이 매장의 방문만 보므로 빈 기본값이 된다 — 아무것도 새지 않는다."""

    def __init__(self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule

    async def get_visit_defaults(self, query: GetVisitDefaultsQuery) -> VisitDefaultsView:
        settings = await self._schedule.ensure(query.ctx)
        last = await self._visits.last_completed_of_pet(query.ctx, query.pet_id)
        if last is None:
            return VisitDefaultsView(source_visit_id=None, duration_minutes=settings.default_duration_minutes,
                                     menus=[])
        active = {m.id: m for m in await self._menus.list_active_by_ids(query.ctx, list(last.menu_ids))}
        return VisitDefaultsView(
            source_visit_id=last.id,
            duration_minutes=last.duration_minutes,
            menus=[MenuBriefView(menu_id=m, name=active[m].name) for m in last.menu_ids if m in active],
        )
