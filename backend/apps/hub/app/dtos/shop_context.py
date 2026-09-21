from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopContext:
    """매장 범위 요청의 컨텍스트 — 누가(member_id) 어느 매장(shop_id)에서 어떤 권한으로 행동하는가.

    매장 범위의 리포지토리 메서드는 이 값을 필수 첫 인자로 받는다.
    컨텍스트 없이는 조회할 수 없게 해서 다른 매장의 데이터가 섞이는 사고를 구조로 막는다.
    """

    shop_id: int
    member_id: int
    role: str
    permissions: frozenset[str]
