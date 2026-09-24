from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class IssueUploadCommand:
    ctx: ShopContext
    kind: str
    content_type: str
    byte_size: int          # 원본 크기(앱 선언). 확인 때 실제 크기로 한 번 더 본다
    width: int
    height: int
    duration_seconds: int | None


@dataclass(frozen=True)
class UploadTargetsView:
    """렌디션마다 PUT 할 URL. 영상은 표시용이 없다."""

    original: str
    display: str | None
    thumb: str


@dataclass(frozen=True)
class IssuedUploadView:
    media_id: int
    puts: UploadTargetsView
    expires_at: datetime
