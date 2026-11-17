from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, NextVisitDraftView, RepeatDraftView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_series_repository import VisitSeriesRepository
from visit.app.services.revisit import pet_cycles, shortest
from visit.domain.entities.visit import CANCELED, COMPLETED, NO_SHOW
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_cycle import next_start
from visit.domain.services.visit_schedule import local_date
from visit.domain.services.visit_series import DEFAULT_COUNT, series_position


class GetNextVisitDraftInteractor(GetNextVisitDraftUseCase):
    """다음 예약 초안(⑬ 설계 3.4) — 날짜와 시간이 늘 채워져 있다. 날짜는 이번 방문 + 아이의 주기(같은 요일),
    시간은 이번 방문의 시작 시각. 주기는 직접 정한 값 → 계산한 값 → 매장의 기본 간격(어림)이고, 가족이면
    아이들 가운데 짧은 쪽이다."""

    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, menus: MenuRepository, *,
        directory: CustomerDirectoryPort, settings: RevisitSettingsRepository, now: Callable[[], datetime],
        series: VisitSeriesRepository,
    ) -> None:
        self._visits = visits
        self._history = history
        self._menus = menus
        self._directory = directory
        self._settings = settings
        self._now = now
        self._series = series

    async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        # 취소·노쇼한 방문에는 다음이 없다. 완료 전(예약됨·미용 중)이라도 초안은 준다 — 완료 시트가
        # 누르기 전에 "언제로 잡히는지"를 보여야 해서다(③-A2).
        if visit.status in (CANCELED, NO_SHOW):
            raise VisitStateConflictError("취소·노쇼한 방문에서는 다음 예약을 잡을 수 없습니다.")
        group = [v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.status not in (CANCELED, NO_SHOW)]
        pet_ids = sorted(v.pet_id for v in group if v.pet_id is not None)
        settings = await self._settings.get(ctx)
        cycles = []
        if pet_ids:
            facts = await self._directory.revisit_facts(ctx, tuple(pet_ids))
            manual = {p: f.grooming_cycle_weeks for p, f in facts.items()}
            # 아직 완료 전이면 이 방문을 "이번"으로 놓는다.
            including = None if visit.status == COMPLETED else local_date(visit.starts_at, ctx.timezone)
            by_pet = await pet_cycles(ctx, pet_ids, manual, self._history, settings,
                                      local_date(self._now(), ctx.timezone), including=including)
            cycles = list(by_pet.values())
        weeks, source = shortest(cycles, settings)
        active = {m.id: m for m in await self._menus.list_active_by_ids(ctx, list(visit.menu_ids))}
        zone = ZoneInfo(ctx.timezone)
        upcoming = await self._history.next_active_after(ctx, visit.customer_id, pet_ids, visit.starts_at)
        return NextVisitDraftView(
            customer_id=visit.customer_id,
            pet_ids=pet_ids,
            starts_at=next_start(visit.starts_at, weeks, ctx.timezone).astimezone(ZoneInfo(ctx.timezone)),
            duration_minutes=visit.duration_minutes,
            menus=[MenuBriefView(menu_id=m, name=active[m].name) for m in visit.menu_ids if m in active],
            interval_weeks=weeks,
            cycle_weeks=weeks,
            cycle_source=source,
            upcoming_starts_at=None if upcoming is None else upcoming.astimezone(zone),
            repeat=await self._repeat_of(ctx, visit),
        )

    async def _repeat_of(self, ctx, visit) -> RepeatDraftView | None:
        """반복 묶음의 마지막 회차면 같은 간격·같은 요일·시각으로 이어 잡을 초안(⑭ 설계 3.7). 횟수는 기본값."""
        if visit.series_id is None:
            return None
        if not series_position(await self._visits.list_series(ctx, visit.series_id), visit).is_last:
            return None
        series = await self._series.get(ctx, visit.series_id)
        starts = next_start(visit.starts_at, series.interval_weeks, ctx.timezone)
        return RepeatDraftView(interval_weeks=series.interval_weeks, count=DEFAULT_COUNT,
                               starts_at=starts.astimezone(ZoneInfo(ctx.timezone)))
