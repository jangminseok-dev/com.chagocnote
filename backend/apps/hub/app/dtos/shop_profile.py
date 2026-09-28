from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopProfile:
    """매장이 밖에 보여 주는 정보. 로그인한 사용자가 없는 자리(공개 알림장)에서 읽는다."""

    shop_id: int
    name: str
    phone: str | None
    address: str | None
    timezone: str
    open: bool                    # 정지(suspended_at)도 폐업(closed_at)도 아니다
