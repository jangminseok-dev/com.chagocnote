from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from search.domain.entities.search_document import SearchDocument


class SearchDocumentRepository(ABC):
    """검색 문서의 쓰기 쪽. 전부 매장 범위다 — 다른 매장의 문서를 읽거나 지우지 않는다."""

    @abstractmethod
    async def list_for_target(self, ctx: ShopContext, scope: str, ref_id: int) -> list[SearchDocument]:
        """그 대상에 드는 문서(domain/services/targets). 벡터와 모델 이름도 함께."""

    @abstractmethod
    async def replace_target(
        self, ctx: ShopContext, scope: str, ref_id: int, documents: list[SearchDocument], now: datetime
    ) -> None:
        """그 대상의 문서를 documents 로 맞춘다 — 없는 것은 지우고 나머지는 (매장, kind, source_id) 로 넣거나 덮는다.
        documents 에 그 대상의 것이 아닌 문서가 있으면 ValueError(아무것도 쓰지 않는다)."""

    @abstractmethod
    async def delete_for_customer(self, ctx: ShopContext, customer_id: int) -> None:
        """그 고객에 딸린 문서를 종류와 상관없이 전부 지운다(익명화)."""
