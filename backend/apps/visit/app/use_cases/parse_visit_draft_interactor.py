from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.parse_visit_draft_dto import (
    DraftCandidateView,
    DraftGuessView,
    DraftPetView,
    ParseVisitDraftCommand,
    VisitDraftView,
)
from visit.app.ports.input.parse_visit_draft_use_case import ParseVisitDraftUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_draft_parser_port import VisitDraftParserPort
from visit.domain.services.visit_schedule import local_date


class ParseVisitDraftInteractor(ParseVisitDraftUseCase):
    """카톡 글 → 예약 초안(설계 7절). 아무것도 쓰지 않는다 — 설정 준비(ensure)만 다른 조회와 같다.

    날짜·시각·메뉴는 해석기가, "누구"는 허브 포트(customer)가 글의 낱말로 찾는다. 결과는 사람이 확인한 뒤 등록 API 로 저장한다.
    """

    def __init__(
        self, schedule: ScheduleRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        parser: VisitDraftParserPort, now: Callable[[], datetime],
    ) -> None:
        self._schedule = schedule
        self._menus = menus
        self._directory = directory
        self._parser = parser
        self._now = now

    async def parse_visit_draft(self, command: ParseVisitDraftCommand) -> VisitDraftView:
        ctx = command.ctx
        settings = await self._schedule.ensure(ctx)
        menus = await self._menus.list(ctx, include_archived=False)
        parsed = self._parser.parse(
            command.text, local_date(self._now(), ctx.timezone), settings.opens_at, settings.closes_at,
            [m.name for m in menus],
        )
        candidates = await self._directory.find_draft_candidates(ctx, parsed.words) if parsed.words else []
        only = candidates[0] if len(candidates) == 1 else None
        return VisitDraftView(
            date=parsed.date,
            time=parsed.time,
            customer_candidates=[
                DraftCandidateView(
                    customer_id=c.customer.customer_id, name=c.customer.name or "",
                    phone_masked=c.customer.phone_masked or "",
                    pets=[DraftPetView(pet_id=p.pet_id, name=p.name or "") for p in c.pets],
                    matched_pet_ids=list(c.matched_pet_ids),
                )
                for c in candidates
            ],
            pet_ids=list(only.matched_pet_ids) if only else [],
            menu_ids=[m.id for m in menus if m.name in parsed.menu_names],
            guessed=DraftGuessView(
                date=parsed.guessed_date, time=parsed.guessed_time,
                who=only is None or not only.exact, menu=parsed.guessed_menu,
            ),
        )
