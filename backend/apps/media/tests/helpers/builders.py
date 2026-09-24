"""media 테스트가 함께 쓰는 값 — 매장 컨텍스트와 발급 선언값."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from media.domain.value_objects.new_media import NewMedia

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
TZ = "Asia/Seoul"


def ctx(shop_id: int = 1, member_id: int = 11) -> ShopContext:
    return ShopContext(shop_id=shop_id, member_id=member_id, role="staff", permissions=STAFF_PERMISSIONS,
                       timezone=TZ)


def new_photo(member_id: int = 11) -> NewMedia:
    return NewMedia(kind="photo", content_type="image/jpeg", width=3000, height=2000, duration_seconds=None,
                    uploaded_by_member_id=member_id)


def new_video(member_id: int = 11) -> NewMedia:
    return NewMedia(kind="video", content_type="video/mp4", width=1920, height=1080, duration_seconds=42,
                    uploaded_by_member_id=member_id)
