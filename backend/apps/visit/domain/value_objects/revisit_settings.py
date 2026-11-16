from __future__ import annotations

from dataclasses import dataclass

from visit.domain.services.visit_cycle import CycleRules

# 매장이 바꿀 수 있는 범위(⑬ 설계 3.7·10절) — DB 의 CHECK 와 같다.
DEFAULT_CYCLE_WEEKS_RANGE = (1, 52)
SOON_DAYS_RANGE = (1, 30)
SAMPLE_VISITS_RANGE = (3, 12)   # 간격이 둘 이상 나와야 계산한 값이라 3번부터
MIN_GAP_DAYS_RANGE = (0, 28)    # 0 이면 손질 방문을 빼지 않는다
MESSAGE_MAX = 300


@dataclass(frozen=True)
class RevisitSettings:
    """매장의 다시 올 때 설정(visit_shop_settings 의 칸 여섯). 처음 값으로 바로 돌고 매장이 바꾼다."""

    default_cycle_weeks: int = 4        # 주기를 모르는 아이의 다음 미용(주)
    revisit_soon_days: int = 7          # 다시 올 날 며칠 전부터 '곧'
    revisit_message: str | None = None  # 안내 글 템플릿 — 없으면 처음 글
    count_unsent_reports: bool = True   # 알림장을 안 보낸 방문을 남은 일로 세기
    cycle_sample_visits: int = 6        # 주기 계산에서 볼 최근 방문 수
    cycle_min_gap_days: int = 7         # 이보다 짧은 간격은 손질로 보고 뺀다

    def rules(self) -> CycleRules:
        return CycleRules(
            default_weeks=self.default_cycle_weeks, sample_visits=self.cycle_sample_visits,
            min_gap_days=self.cycle_min_gap_days, soon_days=self.revisit_soon_days,
        )


DEFAULT_REVISIT_SETTINGS = RevisitSettings()
