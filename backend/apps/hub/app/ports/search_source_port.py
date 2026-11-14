from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.search_source import SourceDocument
from hub.app.dtos.shop_context import ShopContext


class SearchSourcePort(ABC):
    """구현: visit(scope "visit"), customer(scope "pet"·"customer"). 사용: search 의 색인기.

    진입점이 scope 마다 맞는 구현을 색인기에 꽂는다. 자기 것이 아닌 scope 를 받으면 빈 목록이다.
    """

    @abstractmethod
    async def documents(self, ctx: ShopContext, scope: str, ref_id: int) -> list[SourceDocument]:
        """그 대상의 지금 문서 전부. 대상이 없거나 지워졌거나 익명화됐거나 다른 매장이면 빈 목록.
        빈 글은 문서가 아니다. 잠그지 않는다. 글을 로그에 남기지 않는다."""
