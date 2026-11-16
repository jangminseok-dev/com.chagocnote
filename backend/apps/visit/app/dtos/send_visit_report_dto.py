from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SendVisitReportCommand:
    """알림장 보내기. hidden_media_ids 는 뺄 사진·영상 전부다 — 여기에 없는 것은 앞서 뺐더라도 다시 보인다."""

    ctx: ShopContext
    visit_id: int
    hidden_media_ids: tuple[int, ...]
    show_review: bool = True   # 이 알림장에 리뷰 남기기 줄을 넣는가(⑫)
