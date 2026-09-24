from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import CustomerBriefView, PetBriefView


@dataclass(frozen=True)
class ListVisitFeedQuery:
    ctx: ShopContext
    cursor: str | None
    limit: int
    pet_id: int | None   # 있으면 그 아이의 기록만(반려동물 상세의 [기록] 탭)


@dataclass(frozen=True)
class FeedItemView:
    """피드 카드 하나 — 완료 방문. 사진 없는 완료 방문도 나온다(cover 가 None — 앱은 회색 자리)."""

    visit_id: int
    customer: CustomerBriefView
    pet: PetBriefView | None
    completed_at: datetime   # 매장 시간대
    cover: str | None
    menus: list[str]         # 기록의 실제 메뉴, 없으면 예약 메뉴
    care_note: str | None    # 앞 80자
    media_count: int


@dataclass(frozen=True)
class VisitFeedView:
    items: list[FeedItemView]
    next_cursor: str | None
