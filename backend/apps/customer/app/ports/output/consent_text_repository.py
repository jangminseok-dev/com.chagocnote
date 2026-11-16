from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext


class ConsentTextRepository(ABC):
    """매장이 고친 동의서 글. 쌓기만 한다 — 옛 서명을 그 글자로 다시 보여야 한다."""

    @abstractmethod
    async def latest(self, ctx: ShopContext) -> dict[str, tuple[int, str | None]]:
        """토막 → (가장 최근 판, 그 글). 고친 적 없는 토막은 빠진다. 글이 None 이면 기본 글로 되돌린 판이다."""

    @abstractmethod
    async def body_of(self, ctx: ShopContext, part: str, version: int) -> str | None:
        """그 판의 글. 없으면 None."""

    @abstractmethod
    async def append(self, ctx: ShopContext, part: str, body: str | None) -> int:
        """다음 판을 쌓고 그 번호를 돌려준다."""
