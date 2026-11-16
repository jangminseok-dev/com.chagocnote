"""아이들의 미용 주기를 한 번에 읽고 계산한다(⑬ 설계 3.1·4.1) — 반려동물 상세·다음 예약 초안·완료 이벤트·
다시 올 때가 된 아이가 같은 길을 쓴다. 질의 수는 아이 수와 상관없이 고정이다(완료 날짜 하나)."""
from __future__ import annotations

from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.domain.services.visit_cycle import PetCycle, pet_cycle
from visit.domain.value_objects.revisit_settings import RevisitSettings


async def pet_cycles(
    ctx: ShopContext, pet_ids: list[int], manual: dict[int, int | None], history: VisitHistoryRepository,
    settings: RevisitSettings, today: date,
) -> dict[int, PetCycle]:
    """{반려동물 ID: 주기}. manual 은 직접 정한 값(없으면 None 이거나 빠짐). 완료 방문이 없는 아이도 든다."""
    rules = settings.rules()
    days = await history.completed_days(ctx, pet_ids, per_pet=rules.sample_visits)
    return {
        pet_id: pet_cycle(days.get(pet_id, []), manual_weeks=manual.get(pet_id), rules=rules, today=today)
        for pet_id in pet_ids
    }
