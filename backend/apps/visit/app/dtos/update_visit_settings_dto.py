from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.schedule_settings import ScheduleSettings


@dataclass(frozen=True)
class UpdateVisitSettingsCommand:
    """설정 전체를 바꾼다(PUT). 쉬는 요일도 통째로."""

    ctx: ShopContext
    settings: ScheduleSettings
