from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class AppendRecordMediaCommand:
    """사진·영상 하나를 기록의 그 칸(전/후) 맨 뒤에 붙인다. 앱의 업로드 대기열과 방문 상세의 [사진 추가]가 쓴다."""

    ctx: ShopContext
    visit_id: int
    media_id: int
    phase: str
