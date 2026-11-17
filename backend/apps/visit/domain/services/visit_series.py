"""반복 예약(⑭ 설계 3.7) — 회차, `이후 전부` 의 대상, 걸린 회차, 묶음 안의 자리. 순수 함수.

한꺼번에 잡은 예약들은 같은 묶음(`visit_series`)이다. 규칙(간격)은 보여 주려고만 남기고, 뒤에서 예약을 만들어 내지
않는다. 회차는 같은 요일·같은 벽시계 시각이다(`visit_cycle.next_start`). 시각은 UTC 로 받고 돌려준다.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from visit.domain.entities.visit import CANCELED, RESERVED, Visit
from visit.domain.services.visit_cycle import COMPUTED, MANUAL, PetCycle, next_start
from visit.domain.errors import VisitCrossesMidnightError
from visit.domain.services.visit_schedule import BOOKING_HORIZON_DAYS, check_same_day, local_date

MIN_INTERVAL_WEEKS, MAX_INTERVAL_WEEKS = 1, 12
MIN_COUNT, MAX_COUNT, DEFAULT_COUNT = 2, 12, 6

TAKEN = "taken"                 # 그 아이(아이가 없으면 보호자)에게 그 시각 살아 있는 예약이 이미 있다
OUT_OF_RANGE = "out_of_range"   # 예약 가능 범위(오늘 기준 1년) 밖
CROSSES_MIDNIGHT = "crosses_midnight"   # 옮기면 끝나는 시각이 그날 자정을 넘는다

CYCLE = "cycle"   # 간격 기본값의 근거 — 그 아이의 주기(직접 정한 값·계산한 값)
SHOP = "shop"     # 매장의 기본 간격


@dataclass(frozen=True)
class Occurrence:
    index: int            # 회차 번호(1 부터)
    starts_at: datetime   # UTC


@dataclass(frozen=True)
class RepeatInterval:
    weeks: int                 # 1~12 로 자른 간격
    source: str                # cycle · shop
    pet_id: int | None         # cycle 이면 그 주기의 아이
    cycle_weeks: int | None    # cycle 이면 자르기 전 주기


@dataclass(frozen=True)
class SeriesConflict:
    visit_id: int
    pet_id: int | None
    starts_at: datetime   # 옮겨 갈 시각(UTC)
    reason: str           # taken · out_of_range


@dataclass(frozen=True)
class SeriesPosition:
    position: int
    total: int
    is_last: bool


def within_horizon(starts_at: datetime, now: datetime, tz: str) -> bool:
    """예약 가능 범위 — `visit_schedule.check_start` 와 같은 판정(매장 시간대의 날짜로 앞뒤 1년)."""
    if abs(starts_at - now) > timedelta(days=BOOKING_HORIZON_DAYS + 1):
        return False
    return abs((local_date(starts_at, tz) - local_date(now, tz)).days) <= BOOKING_HORIZON_DAYS


def plan_occurrences(
    first: datetime, interval_weeks: int, count: int, tz: str, now: datetime,
) -> tuple[list[Occurrence], int]:
    """first 부터 interval_weeks 주마다 count 번. 범위 밖 회차는 빼고, 뺀 수를 함께 돌려준다."""
    planned = [Occurrence(i, next_start(first, interval_weeks * (i - 1), tz)) for i in range(1, count + 1)]
    kept = [o for o in planned if within_horizon(o.starts_at, now, tz)]
    return kept, len(planned) - len(kept)


def clip_interval(weeks: int) -> int:
    return max(MIN_INTERVAL_WEEKS, min(MAX_INTERVAL_WEEKS, weeks))


def repeat_interval(cycles: dict[int, PetCycle], shop_default_weeks: int) -> RepeatInterval:
    """간격의 기본값(공통 11절) — 아이들 가운데 짧은 쪽(⑬ 의 가족 규칙과 같다). 그 아이의 주기를 알면(직접·계산)
    그 값을, 모르면 매장의 기본 간격을 1~12 로 자른다."""
    if not cycles:
        return RepeatInterval(clip_interval(shop_default_weeks), SHOP, None, None)
    pet_id, chosen = min(cycles.items(), key=lambda item: (item[1].weeks, item[0]))
    if chosen.source in (MANUAL, COMPUTED):
        return RepeatInterval(clip_interval(chosen.weeks), CYCLE, pet_id, chosen.weeks)
    return RepeatInterval(clip_interval(shop_default_weeks), SHOP, None, None)


def _wall(moment: datetime, tz: str) -> datetime:
    return moment.astimezone(ZoneInfo(tz)).replace(tzinfo=None)


def wall_delta(before: datetime, after: datetime, tz: str) -> timedelta:
    """매장 시간대 벽시계로 본 두 시각의 차이."""
    return _wall(after, tz) - _wall(before, tz)


def wall_shift(starts_at: datetime, delta: timedelta, tz: str) -> datetime:
    """벽시계로 delta 만큼 민 시각(UTC)."""
    return (_wall(starts_at, tz) + delta).replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def following_of(
    series: Sequence[Visit], anchors: Sequence[Visit], *, family: bool, skip_ids: frozenset[int] = frozenset(),
) -> list[Visit]:
    """`이후 전부` 의 대상 — 같은 묶음에서 이 회차 이상의 예약됨. family 가 거짓이면 anchors 의 아이들만."""
    start = anchors[0].starts_at
    pets = {a.pet_id for a in anchors}
    picked = [
        v for v in series
        if v.status == RESERVED and v.starts_at >= start and (family or v.pet_id in pets) and v.id not in skip_ids
    ]
    return sorted(picked, key=lambda v: (v.starts_at, v.id))


def earliest_ids(visits: Sequence[Visit]) -> frozenset[int]:
    """시작 시각이 가장 이른 방문들 — `이후 전부` 에서 보호자에게 안내를 내는 가장 가까운 회차."""
    if not visits:
        return frozenset()
    first = min(v.starts_at for v in visits)
    return frozenset(v.id for v in visits if v.starts_at == first)


def move_order(moves: Sequence[tuple[Visit, datetime]]) -> list[tuple[Visit, datetime]]:
    """옮기는 차례 — 늦게 미는 묶음은 지금 시각이 늦은 것부터, 당기는 묶음은 이른 것부터.

    같은 아이가 다음 회차의 옛 자리로 갈 때 부분 유일 색인(같은 아이·같은 시각의 살아 있는 예약)에 걸리지 않게 한다.
    """
    later = any(new > visit.starts_at for visit, new in moves)
    return sorted(moves, key=lambda m: (m[0].starts_at, m[0].id), reverse=later)


def _same_slot(a: Visit, b: Visit) -> bool:
    if a.pet_id is not None:
        return a.pet_id == b.pet_id
    return b.pet_id is None and a.customer_id == b.customer_id


def _crosses_midnight(starts_at: datetime, minutes: int, tz: str) -> bool:
    try:
        check_same_day(starts_at, minutes, tz)
    except VisitCrossesMidnightError:
        return True
    return False


def conflicts_of(
    moves: Sequence[tuple[Visit, datetime]], occupied: Sequence[Visit], now: datetime, tz: str,
    duration_minutes: int | None = None,
) -> list[SeriesConflict]:
    """옮겨 갈 자리에 걸리는 회차. occupied 는 그 보호자의 새 시각들의 살아 있는 방문 — 옮기는 방문은 부르는 쪽이 뺀다.

    걸린 회차는 빼고 다시 보내면 제자리에 선다 — 그러면 그 옛 자리로 가려던 앞 회차가 다시 걸린다(주마다 묶음을 1주
    밀 때). 그래서 걸린 회차를 제자리에 선 것으로 놓고 더 걸리는 것이 없을 때까지 따라가 한 번에 돌려준다.
    duration_minutes 가 있으면(고치기의 새 소요) 그 값으로 자정을 본다.
    """
    ordered = sorted(moves, key=lambda m: (m[0].starts_at, m[0].id))
    staying = list(occupied)
    found: dict[int, SeriesConflict] = {}
    grew = True
    while grew:
        grew = False
        for visit, new in ordered:
            if visit.id in found:
                continue
            reason = None
            if not within_horizon(new, now, tz):
                reason = OUT_OF_RANGE
            elif _crosses_midnight(new, duration_minutes or visit.duration_minutes, tz):
                reason = CROSSES_MIDNIGHT
            elif any(o.starts_at == new and _same_slot(visit, o) for o in staying):
                reason = TAKEN
            if reason is not None:
                found[visit.id] = SeriesConflict(visit.id, visit.pet_id, new, reason)
                staying.append(visit)   # 빼면 옛 시각에 남는다
                grew = True
    return [found[v.id] for v, _ in ordered if v.id in found]


def series_position(series: Sequence[Visit], visit: Visit) -> SeriesPosition:
    """묶음 안의 자리(`6번 중 3번째`) — 그 아이(아이가 없으면 보호자만의 방문)의 회차를 취소를 빼고 센다. 가족의
    시각이 `콩이만` 옮기기로 갈려도 아이마다 맞다. 그 방문 자신이 취소됐으면 자신은 넣는다."""
    mine = [v for v in series if v.pet_id == visit.pet_id]
    starts = sorted({v.starts_at for v in mine if v.status != CANCELED or v.id == visit.id} | {visit.starts_at})
    position = starts.index(visit.starts_at) + 1
    return SeriesPosition(position, len(starts), position == len(starts))
