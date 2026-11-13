"""다시 올 때가 지난 아이(설계 ⑧ 3.3) — 저장소의 후보에서 무지개다리·익명화·지운 아이를 뺀다.

요약의 수와 목록이 같은 거르기를 쓴다. 후보는 지난 한 해에 온 아이로 묶여 있어 한 번에 다 읽는다.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from hub.app.dtos.family_brief import PetBrief
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.sales_repository import SalesRepository
from visit.app.services.pet_cards import showable_pets
from visit.domain.value_objects.sales import DuePet


def start_of_day(ctx: ShopContext, day: date) -> datetime:
    """매장 시간대의 그날 0시. '앞으로의 예약'은 여기서부터 센다 — 10시 예약을 10시 20분에 아직 시작하지
    않았다고 그 아이가 다시 올 때가 지난 아이로 나오거나 남은 예약에서 빠지면 안 된다."""
    return datetime.combine(day, time.min, ZoneInfo(ctx.timezone))


async def due_pets(
    ctx: ShopContext, sales: SalesRepository, directory: CustomerDirectoryPort, today: date,
) -> tuple[list[DuePet], dict[int, PetBrief]]:
    """(다시 올 때가 지난 아이들 — 오래된 순, 그 아이들의 요약). today 는 매장 시간대의 오늘이다."""
    candidates = await sales.due_candidates(ctx, today, start_of_day(ctx, today))
    pets = await showable_pets(ctx, [c.pet_id for c in candidates], directory)
    due = [c for c in candidates if c.pet_id in pets and not pets[c.pet_id].passed_away]
    return due, pets
