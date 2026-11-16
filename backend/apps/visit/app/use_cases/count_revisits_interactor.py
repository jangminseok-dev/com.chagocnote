from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.count_revisits_dto import CountRevisitsQuery, RevisitCountsView
from visit.app.ports.input.count_revisits_use_case import CountRevisitsUseCase
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.services.revisit import revisit_board
from visit.domain.services.visit_schedule import local_date


class CountRevisitsInteractor(CountRevisitsUseCase):
    """캘린더 탭의 `다시 올 때가 된 아이 N`(⑬ 설계 3.3·4.3) — 달력과 따로 읽는다(늦게 와도 달력은 먼저 뜬다).
    목록과 같은 거르기(`revisit_board`)라 수와 목록이 같다."""

    def __init__(
        self, history: VisitHistoryRepository, directory: CustomerDirectoryPort, settings: RevisitSettingsRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._history = history
        self._directory = directory
        self._settings = settings
        self._now = now

    async def count_revisits(self, query: CountRevisitsQuery) -> RevisitCountsView:
        ctx = query.ctx
        board = await revisit_board(ctx, self._history, self._directory, await self._settings.get(ctx),
                                    local_date(self._now(), ctx.timezone))
        return RevisitCountsView(
            soon=sum(1 for r in board.rows if r.bucket == "soon"),
            due=sum(1 for r in board.rows if r.bucket == "due"),
        )
