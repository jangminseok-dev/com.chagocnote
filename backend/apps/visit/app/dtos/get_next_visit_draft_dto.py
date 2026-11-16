from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import MenuBriefView


@dataclass(frozen=True)
class GetNextVisitDraftQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class NextVisitDraftView:
    """완료한 방문 기준의 다음 예약 초안. 저장하지 않는다 — 앱이 예약 ② 화면을 이 값으로 채워 연다."""

    customer_id: int
    pet_ids: list[int]           # 같은 묶음으로 완료한 아이들(보호자만이면 빈 목록)
    starts_at: datetime          # 매장 시간대, 주기 뒤 같은 요일·같은 시각
    duration_minutes: int
    menus: list[MenuBriefView]   # 보관한 메뉴는 뺀다
    interval_weeks: int          # (예전 앱이 읽는 칸 — cycle_weeks 와 같다)
    cycle_weeks: int             # 날짜에 쓴 주(⑬)
    cycle_source: str            # manual · computed · single · none — 완료 시트가 "보통 오는 간격"·"어림"을 가른다
