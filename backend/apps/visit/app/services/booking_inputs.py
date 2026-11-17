"""예약을 잡을 때의 입력 — 고른 메뉴와 소요(등록·반복 미리 보기가 같은 규칙을 쓴다)."""
from __future__ import annotations

from collections.abc import Sequence

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.errors import MenuNotAvailableError
from visit.domain.services.visit_duration import default_duration
from visit.domain.services.visit_schedule import check_duration
from visit.domain.value_objects.schedule_settings import ScheduleSettings


async def chosen_duration(
    ctx: ShopContext, menu_ids: Sequence[int], duration_minutes: int | None, menus: MenuRepository,
    settings: ScheduleSettings,
) -> int:
    """고를 수 없는 메뉴(보관·다른 매장)가 있으면 MenuNotAvailableError. 소요가 없으면 메뉴로 센다."""
    found = await menus.list_active_by_ids(ctx, list(menu_ids))
    if len(found) != len(menu_ids):
        raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")
    duration = duration_minutes if duration_minutes is not None else default_duration(
        found, settings.default_duration_minutes)
    check_duration(duration)
    return duration
