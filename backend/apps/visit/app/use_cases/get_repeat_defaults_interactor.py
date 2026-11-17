from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.get_repeat_defaults_dto import GetRepeatDefaultsQuery, RepeatDefaultsView
from visit.app.ports.input.get_repeat_defaults_use_case import GetRepeatDefaultsUseCase
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.services.revisit import pet_cycles
from visit.domain.services.visit_schedule import local_date
from visit.domain.services.visit_series import DEFAULT_COUNT, repeat_interval


class GetRepeatDefaultsInteractor(GetRepeatDefaultsUseCase):
    """반복의 간격·횟수 기본값(⑭ 설계 3.7, 공통 11절). 간격은 ⑬ 의 아이 주기(가족이면 짧은 쪽)를 1~12 로 자른
    값이고, 주기를 모르면 매장의 기본 간격이다. 횟수는 6(⑭-4 가 남은 횟수권으로 바꾼다). 저장하지 않는다."""

    def __init__(
        self, history: VisitHistoryRepository, *, directory: CustomerDirectoryPort,
        settings: RevisitSettingsRepository, now: Callable[[], datetime],
    ) -> None:
        self._history = history
        self._directory = directory
        self._settings = settings
        self._now = now

    async def get_repeat_defaults(self, query: GetRepeatDefaultsQuery) -> RepeatDefaultsView:
        ctx = query.ctx
        settings = await self._settings.get(ctx)
        cycles = {}
        if query.pet_ids:
            facts = await self._directory.revisit_facts(ctx, query.pet_ids)
            manual = {p: f.grooming_cycle_weeks for p, f in facts.items()}
            cycles = await pet_cycles(ctx, list(query.pet_ids), manual, self._history, settings,
                                      local_date(self._now(), ctx.timezone))
        interval = repeat_interval(cycles, settings.default_cycle_weeks)
        return RepeatDefaultsView(interval_weeks=interval.weeks, source=interval.source, pet_id=interval.pet_id,
                                  cycle_weeks=interval.cycle_weeks, count=DEFAULT_COUNT)
