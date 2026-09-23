"""저장한 뒤 돌려줄 경고(설계 6.3) — 겹침·휴무·영업시간 밖. 막지 않는다."""
from __future__ import annotations

from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.services.visit_schedule import Occupied, day_bounds, local_date, warnings_for
from visit.domain.value_objects.schedule_settings import ScheduleSettings


async def warnings_after_save(
    ctx: ShopContext, customer_id: int, starts_at: datetime, duration_minutes: int, settings: ScheduleSettings,
    visits: VisitRepository, schedule: ScheduleRepository,
) -> list[str]:
    """방금 저장한 묶음(같은 보호자 + 같은 시작 시각)의 경고. 저장한 방문 자신은 같은 묶음이라 겹침에서 빠진다."""
    tz = ctx.timezone
    day = local_date(starts_at, tz)
    start, end = day_bounds(day, tz)
    occupied = [Occupied(v.starts_at, v.ends_at, v.group_key) for v in await visits.list_occupied(ctx, start, end)]
    closed = frozenset(c.day for c in await schedule.list_closed_dates(ctx, day, day))
    return warnings_for(starts_at, duration_minutes, (customer_id, starts_at), tz, settings, closed, occupied)
