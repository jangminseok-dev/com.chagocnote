"""아이의 미용 주기와 다음 올 때(⑬ 설계 3.1) — 다음 예약 초안·알림 줄·다시 올 때가 된 아이가 같은 값을 쓴다.

주기는 ① 직접 정한 값(1~52주) → ② 지난 완료 방문에서 계산한 값(최근 N번의 이웃 간격 가운데 손질로 보이는 짧은
간격을 버리고, **간격이 둘 이상일 때만** 중앙값) → ③ 모르면 매장의 기본 간격으로 어림한다. 간격 하나는 주기가
아니다 — 글로만 알려 주고 날짜에는 기본 간격을 쓴다(2주 간격으로 두 번 온 아이가 15일째에 '지남'이 되지 않게).
계산은 읽을 때 한다. 저장하지 않는다. 날짜는 모두 매장 시간대의 날짜다.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo

DEFAULT_WEEKS = 4
MIN_WEEKS = 1
MAX_WEEKS = 52
LOOKBACK_DAYS = 730   # 2년보다 오래된 방문은 계산에 넣지 않는다

MANUAL = "manual"
COMPUTED = "computed"
SINGLE = "single"
NONE = "none"


@dataclass(frozen=True)
class CycleRules:
    """매장의 값(예약 설정) — 처음 값이 기본이고 매장이 바꾼다."""

    default_weeks: int = DEFAULT_WEEKS   # 주기를 모르는 아이의 간격(1~52주)
    sample_visits: int = 6               # 계산에서 볼 최근 완료 방문 수(3~12)
    min_gap_days: int = 7                # 이보다 짧은 간격은 손질로 보고 버린다(0~28, 0 이면 버리지 않는다)
    soon_days: int = 7                   # 다음 올 때가 오늘부터 이 날 수 안이면 '곧'(1~30)


@dataclass(frozen=True)
class PetCycle:
    weeks: int                        # 날짜에 쓰는 주(직접·계산이면 그 값, 아니면 매장의 기본 간격)
    source: str                       # manual · computed · single · none
    interval_count: int               # 버리고 남은 간격의 수
    last_interval_weeks: int | None   # 가장 최근 간격(주) — single 의 "지난번에는 N주 만에"
    last_visit_date: date | None      # 마지막 완료 방문의 날
    due_date: date | None             # 다음 올 때 = 마지막 완료 방문의 날 + weeks
    estimated: bool                   # 날짜가 어림인가(single · none)


def _weeks(days: float) -> int:
    """날 수를 주로 반올림(반은 올린다)해 1~52 로 자른다."""
    return max(MIN_WEEKS, min(MAX_WEEKS, math.floor(days / 7 + 0.5)))


def pet_cycle(
    completed_days: Sequence[date], *, manual_weeks: int | None, rules: CycleRules, today: date,
) -> PetCycle:
    """그 아이의 완료 방문 날짜들(순서 무관)과 직접 정한 값으로 주기를 낸다."""
    last_visit = max(completed_days) if completed_days else None
    window = sorted(d for d in completed_days if d >= today - timedelta(days=LOOKBACK_DAYS))
    recent = window[-rules.sample_visits:]
    gaps = [(b - a).days for a, b in zip(recent, recent[1:])]
    gaps = [g for g in gaps if g >= rules.min_gap_days]
    last_interval = _weeks(gaps[-1]) if gaps else None

    if manual_weeks is not None:
        weeks, source = manual_weeks, MANUAL
    elif len(gaps) >= 2:
        weeks, source = _weeks(median(gaps)), COMPUTED
    else:
        weeks, source = rules.default_weeks, (SINGLE if gaps else NONE)
    return PetCycle(
        weeks=weeks,
        source=source,
        interval_count=len(gaps),
        last_interval_weeks=last_interval,
        last_visit_date=last_visit,
        due_date=last_visit + timedelta(weeks=weeks) if last_visit else None,
        estimated=source in (SINGLE, NONE),
    )


def bucket_of(cycle: PetCycle, today: date, soon_days: int) -> str | None:
    """다시 올 때가 된 아이의 묶음 — 'due'(다음 올 때가 지났다 — 어림 포함), 'soon'(오늘부터 soon_days 안 —
    주기를 아는 아이만, 모르는 주기로 "곧 올 아이"라고 말하지 않는다), 아니면 None."""
    if cycle.due_date is None:
        return None
    if cycle.due_date < today:
        return "due"
    if not cycle.estimated and cycle.due_date <= today + timedelta(days=soon_days):
        return "soon"
    return None


def next_start(source_starts_at: datetime, weeks: int, tz: str) -> datetime:
    """weeks 주 뒤의 같은 요일·같은 벽시계 시각."""
    local = source_starts_at.astimezone(ZoneInfo(tz))
    wall = local.replace(tzinfo=None) + timedelta(weeks=weeks)
    return wall.replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
