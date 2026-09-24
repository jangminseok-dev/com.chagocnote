from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.menu import Menu


class MenuRepository(ABC):
    """매장 메뉴표. 메뉴는 지우지 않고 보관한다. 새 메뉴를 만들기 전에 설정 행이 있어야 한다(외래 키)."""

    @abstractmethod
    async def list(self, ctx: ShopContext, include_archived: bool) -> list[Menu]:
        """순서(sort_order) 대로."""

    @abstractmethod
    async def list_active_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
        """요청 본문이 고른 메뉴 가운데 이 매장의 보관하지 않은 것만."""

    @abstractmethod
    async def create(
        self, ctx: ShopContext, name: str, default_duration_minutes: int | None, price: int | None
    ) -> Menu:
        """맨 뒤 순서로 넣는다. 보관하지 않은 메뉴와 이름이 겹치면 MenuNameTakenError."""

    @abstractmethod
    async def update(
        self, ctx: ShopContext, menu_id: int, name: str, default_duration_minutes: int | None,
        sort_order: int, price: int | None,
    ) -> Menu:
        """없거나 다른 매장이면 MenuNotFoundError. 이름이 겹치면 MenuNameTakenError."""

    @abstractmethod
    async def archive(self, ctx: ShopContext, menu_id: int) -> Menu:
        """이미 보관했으면 처음 시각을 지킨다. 없거나 다른 매장이면 MenuNotFoundError."""
