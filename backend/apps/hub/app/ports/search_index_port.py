from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext


class SearchIndexPort(ABC):
    """구현: search. 사용: customer(고객 익명화)."""

    @abstractmethod
    async def forget_customer(self, ctx: ShopContext, customer_id: int) -> None:
        """그 고객에 딸린 검색 문서를 종류와 상관없이 전부 지우고, 다시 맞출 줄을 하나 넣는다.

        부르는 쪽(익명화)의 트랜잭션 안에서 한다 — 색인기를 기다리지 않고 곧바로 검색에서 사라지고, 익명화가
        되돌려지면 함께 되돌려진다(⑨ 설계 3.5)."""
