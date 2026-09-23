from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopAccessRecord:
    """한 유저가 한 매장에 대해 가진 소속·역할·권한과 그 매장의 상태. 매 요청마다 DB 에서 읽는다."""

    member_id: int
    role: str
    permissions: frozenset[str]
    shop_suspended: bool
    shop_closed: bool
    timezone: str
