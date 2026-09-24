from __future__ import annotations

from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.get_visit_dto import GetVisitQuery, PreviousVisitView, VisitDetailView
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.services.visit_reader import describe_visits


class GetVisitInteractor(GetVisitUseCase):
    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, ledger: VisitLedgerRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort,
    ) -> None:
        self._visits = visits
        self._history = history
        self._ledger = ledger
        self._menus = menus
        self._directory = directory

    async def get_visit(self, query: GetVisitQuery) -> VisitDetailView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        group = [v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.id != visit.id]
        previous = await self._history.last_completed_before(ctx, visit.customer_id, visit.pet_id, visit.starts_at)
        [view, *group_views] = await describe_visits(ctx, [visit, *group], self._directory, self._menus)
        return VisitDetailView(
            visit=view,
            group=group_views,
            previous_visit=PreviousVisitView(
                visit_id=previous.id, starts_at=previous.starts_at.astimezone(ZoneInfo(ctx.timezone))
            ) if previous else None,
            no_show_count=await self._ledger.count_no_show(ctx, visit.customer_id),
        )
