from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.get_day_wrap_up_dto import (
    REPORT_UNSENT,
    UNPAID,
    UNRESOLVED,
    DayWrapUpView,
    GetDayWrapUpQuery,
    PrefillView,
    WrapUpCardView,
)
from visit.app.ports.input.get_day_wrap_up_use_case import GetDayWrapUpUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.pet_cards import pet_cards, showable_pets
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import COMPLETED, Visit
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_board import is_unresolved
from visit.domain.services.visit_marks import is_report_unsent, is_unpaid
from visit.domain.services.visit_schedule import day_bounds, local_date

# 종류의 차례와 그 장을 끝내는 데 드는 권한(지금의 각 동작 그대로 — 설계 3.6).
KINDS = ((UNRESOLVED, "reservation:write"), (UNPAID, "sales:write"), (REPORT_UNSENT, "record:write"))


class GetDayWrapUpInteractor(GetDayWrapUpUseCase):
    """하루 마무리 — 그날의 남은 일을 장으로(⑬ 설계 3.6). 하루 머리의 수와 같은 판정(`visit_marks`·`is_unresolved`)을
    쓰고, 익명화한 고객의 방문은 끝낼 수 없으므로 남은 일이 아니다(하루·달력의 수도 같다). 앞날에는 남은 일이 없다.
    질의 수는 방문 수와 상관없다."""

    def __init__(
        self, board: VisitBoardRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        records: VisitRecordRepository, library: MediaLibraryPort, reports: ReportRepository,
        revisit_settings: RevisitSettingsRepository, now: Callable[[], datetime],
    ) -> None:
        self._board = board
        self._menus = menus
        self._directory = directory
        self._records = records
        self._library = library
        self._reports = reports
        self._revisit_settings = revisit_settings
        self._now = now

    async def get_day_wrap_up(self, query: GetDayWrapUpQuery) -> DayWrapUpView:
        ctx, tz, day = query.ctx, query.ctx.timezone, query.day
        if not (2000 <= day.year <= 2100):
            raise VisitInputError("날짜가 올바르지 않습니다.")
        today = local_date(self._now(), tz)
        allowed = [kind for kind, permission in KINDS if permission in ctx.permissions]
        if day > today or not allowed:
            return DayWrapUpView(date=day, cards=[])

        start, end = day_bounds(day, tz)
        visits = sorted(await self._board.list_between(ctx, start, end), key=lambda v: (v.starts_at, v.id))
        views = {view.visit_id: view for view in await describe_visits(ctx, visits, self._directory, self._menus)}
        visits = [v for v in visits if views[v.id].customer.name is not None]   # 익명화한 고객은 끝낼 수 없다
        done_ids = [v.id for v in visits if v.status == COMPLETED]
        recorded = await self._records.list_many(ctx, done_ids) if done_ids else {}
        ever = await self._reports.visit_ids_with_report(ctx, done_ids) \
            if done_ids and REPORT_UNSENT in allowed else set()
        count_unsent = (await self._revisit_settings.get(ctx)).count_unsent_reports \
            if REPORT_UNSENT in allowed else False

        def wanted(kind: str, visit: Visit) -> bool:
            record = recorded.get(visit.id)
            if kind == UNRESOLVED:
                return is_unresolved(visit, today, tz)
            if kind == UNPAID:
                return is_unpaid(visit, record)
            return is_report_unsent(visit, record, ever_sent=visit.id in ever, count=count_unsent)

        found = [(kind, visit) for kind in allowed for visit in visits if wanted(kind, visit)]
        prefill = await self._prefill(ctx, [v for kind, v in found if kind == UNPAID], recorded)
        pet_ids = [v.pet_id for _, v in found if v.pet_id is not None]
        cards = await pet_cards(ctx, await showable_pets(ctx, pet_ids, self._directory), pet_ids,
                                self._records, self._library)
        return DayWrapUpView(date=day, cards=[
            WrapUpCardView(
                kind=kind, visit=views[visit.id],
                photo_url=cards[visit.pet_id].photo_url if visit.pet_id in cards else None,
                prefill=prefill[visit.id] if kind == UNPAID else None,
            )
            for kind, visit in found
        ])

    async def _prefill(
        self, ctx, unpaid: list[Visit], recorded: dict[int, VisitRecord]
    ) -> dict[int, PrefillView]:
        """총액 = 기록의 총액 → 기록의 항목 합 → 예약한 메뉴의 정가 합(값이 없는 메뉴는 빼고, 하나도 없으면 None) —
        기록 화면의 채움 규칙과 같다. 결제 수단 = 기록의 것 → 그 고객이 가장 최근에 적은 것."""
        if not unpaid:
            return {}
        menu_ids = sorted({m for v in unpaid if not _has_amount(recorded.get(v.id)) for m in v.menu_ids})
        prices = {m.id: m.price for m in await self._menus.list_by_ids(ctx, menu_ids)} if menu_ids else {}
        latest = await self._records.latest_payment_methods(ctx, sorted({v.customer_id for v in unpaid}))

        def total_of(visit: Visit) -> int | None:
            record = recorded.get(visit.id)
            if record is not None and record.total_amount is not None:
                return record.total_amount
            if record is not None and record.items:
                return sum(item.amount for item in record.items)
            priced = [prices[m] for m in visit.menu_ids if prices.get(m) is not None]
            return sum(priced) if priced else None

        def method_of(visit: Visit) -> str | None:
            record = recorded.get(visit.id)
            if record is not None and record.payment_method is not None:
                return record.payment_method
            return latest.get(visit.customer_id)

        return {v.id: PrefillView(total_amount=total_of(v), payment_method=method_of(v)) for v in unpaid}


def _has_amount(record: VisitRecord | None) -> bool:
    return record is not None and (record.total_amount is not None or bool(record.items))
