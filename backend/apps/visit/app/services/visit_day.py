"""매장 시간대의 하루 경계."""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from hub.app.dtos.shop_context import ShopContext


def start_of_day(ctx: ShopContext, day: date) -> datetime:
    """매장 시간대의 그날 0시. '앞으로의 예약'은 여기서부터 센다 — 10시 예약을 10시 20분에 아직 시작하지
    않았다고 그 아이가 다시 올 때가 된 아이로 나오거나 남은 예약에서 빠지면 안 된다."""
    return datetime.combine(day, time.min, ZoneInfo(ctx.timezone))
