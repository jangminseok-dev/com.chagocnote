from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.errors import FamilyNotFoundError
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.check_view_dto import CheckView
from visit.app.dtos.get_visit_checks_dto import GetVisitChecksQuery, PetChecksView, VisitChecksView
from visit.app.ports.input.get_visit_checks_use_case import GetVisitChecksUseCase
from visit.app.ports.output.visit_check_repository import VisitCheckRepository
from visit.app.services.visit_checks import CheckTarget, read_checks
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_checks import CUSTOMER, PET
from visit.domain.services.visit_schedule import BOOKING_HORIZON_DAYS, day_bounds, local_date

MAX_PETS = 10
_OWNER_KEY = 0   # 보호자 항목을 묻는 대상의 key — 반려동물 ID(1 이상)와 겹치지 않는다


class GetVisitChecksInteractor(GetVisitChecksUseCase):
    """예약 등록 화면의 미리 보기(③-B). 아무것도 쓰지 않고, 예약을 막지도 않는다."""

    def __init__(
        self, directory: CustomerDirectoryPort, checks: VisitCheckRepository, now: Callable[[], datetime]
    ) -> None:
        self._directory = directory
        self._checks = checks
        self._now = now

    async def get_visit_checks(self, query: GetVisitChecksQuery) -> VisitChecksView:
        ctx, day = query.ctx, query.day
        today = local_date(self._now(), ctx.timezone)
        if len(query.pet_ids) > MAX_PETS:
            raise VisitInputError("반려동물은 한 번에 10마리까지 확인할 수 있습니다.")
        if abs((day - today).days) > BOOKING_HORIZON_DAYS:
            raise VisitInputError("예약은 오늘 기준 앞뒤 1년 안에서만 잡을 수 있습니다.")
        # 그날 앞서 끝낸 방문도 이력이다 — 기준 시각은 그 날의 끝(다음 날 0시).
        before = day_bounds(day, ctx.timezone)[1]
        pet_ids = list(dict.fromkeys(query.pet_ids))
        targets = [CheckTarget(key=_OWNER_KEY, customer_id=query.customer_id, pet_id=None, on=day, before=before)]
        targets += [
            CheckTarget(key=pet_id, customer_id=query.customer_id, pet_id=pet_id, on=day, before=before)
            for pet_id in pet_ids
        ]
        read = await read_checks(ctx, targets, self._directory, self._checks, today)
        if query.customer_id not in read.known_customers:
            raise FamilyNotFoundError("고객을 찾을 수 없습니다.")
        return VisitChecksView(
            customer=[CheckView.of(c) for c in read.by_key[_OWNER_KEY] if c.scope == CUSTOMER],
            pets=[
                PetChecksView(
                    pet_id=pet_id,
                    checks=[CheckView.of(c) for c in read.by_key[pet_id] if c.scope == PET],
                )
                for pet_id in pet_ids if pet_id in read.known_pets
            ],
        )
