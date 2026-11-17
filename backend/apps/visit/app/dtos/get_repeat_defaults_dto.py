from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetRepeatDefaultsQuery:
    ctx: ShopContext
    customer_id: int               # ⑭-4 가 남은 횟수권으로 횟수 기본값을 정할 때 쓴다
    pet_ids: tuple[int, ...]


@dataclass(frozen=True)
class RepeatDefaultsView:
    """반복 시트를 처음 열 때 채울 값(⑭ 설계 3.7) — 고칠 수 있다."""

    interval_weeks: int        # 1~12
    source: str                # cycle(그 아이의 주기) · shop(매장의 기본 간격)
    pet_id: int | None         # cycle 이면 그 주기의 아이 — 앱이 "콩이는 보통 5주마다 와요"를 쓴다
    cycle_weeks: int | None    # cycle 이면 자르기 전 주기
    count: int                 # 첫 예약을 포함한 횟수
