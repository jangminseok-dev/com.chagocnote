from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext


def system_context(shop_id: int, timezone: str = "Asia/Seoul") -> ShopContext:
    """요청 밖(디스패처)에서 ShopContext 를 만드는 유일한 곳. 권한이 비어 있고 포트 읽기와 알림 표 쓰기에만 쓴다.

    멤버가 없어 member_id 는 0 이다. 시간대는 ShopProfilePort 에서 읽은 매장 값을 넣는다 — 시각 계산이 없는
    저장(status 바꾸기)만이면 기본값으로 둔다.
    """
    return ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset(), timezone=timezone)
