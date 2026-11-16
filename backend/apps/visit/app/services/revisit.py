"""아이들의 미용 주기를 한 번에 읽고 계산한다(⑬ 설계 3.1·4.1) — 반려동물 상세·다음 예약 초안·완료 이벤트·
다시 올 때가 된 아이가 같은 길을 쓴다. 질의 수는 아이 수와 상관없이 고정이다(완료 날짜 하나)."""
from __future__ import annotations

from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.domain.services.visit_cycle import NONE, PetCycle, pet_cycle
from visit.domain.value_objects.revisit_settings import RevisitSettings


async def pet_cycles(
    ctx: ShopContext, pet_ids: list[int], manual: dict[int, int | None], history: VisitHistoryRepository,
    settings: RevisitSettings, today: date, including: date | None = None,
) -> dict[int, PetCycle]:
    """{반려동물 ID: 주기}. manual 은 직접 정한 값(없으면 None 이거나 빠짐). 완료 방문이 없는 아이도 든다.
    including 은 아직 완료하지 않은 "이번" 방문의 날 — 완료 시트가 누르기 전에 초안을 보일 때 넣는다."""
    rules = settings.rules()
    days = await history.completed_days(ctx, pet_ids, per_pet=rules.sample_visits)
    cycles = {}
    for pet_id in pet_ids:
        mine = days.get(pet_id, [])
        if including is not None and including not in mine:
            mine = [including, *mine][: rules.sample_visits]
        cycles[pet_id] = pet_cycle(mine, manual_weeks=manual.get(pet_id), rules=rules, today=today)
    return cycles


def shortest(cycles: list[PetCycle], settings: RevisitSettings) -> tuple[int, str]:
    """가족 묶음의 주기 — 아이들 가운데 짧은 쪽(⑬ 설계 3.4, 공통 11절). 아이가 없으면 매장의 기본 간격."""
    if not cycles:
        return settings.default_cycle_weeks, NONE
    chosen = min(cycles, key=lambda c: c.weeks)
    return chosen.weeks, chosen.source
