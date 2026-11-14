from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from search.domain.entities.search_document import Candidate, PetScope
from search.domain.services.rank_fusion import CANDIDATE_LIMIT


class SearchCandidateRepository(ABC):
    """검색의 읽기 쪽 — 이 매장의 문서 가운데 후보를 고른다. 검색어·글·벡터를 로그에 남기지 않는다."""

    @abstractmethod
    async def lexical(
        self, ctx: ShopContext, q: str, pattern: str, pet_scope: PetScope | None, limit: int = CANDIDATE_LIMIT
    ) -> list[Candidate]:
        """글자로 걸리는 문서 — 글에 검색어가 그대로 든 것(pattern, ILIKE)이 먼저, 그다음 trigram word_similarity 가
        기준 이상인 것. 가까운 순, 같으면 최근 방문·나중 문서가 앞."""

    @abstractmethod
    async def semantic(
        self, ctx: ShopContext, vector: tuple[float, ...], pet_scope: PetScope | None, limit: int = CANDIDATE_LIMIT
    ) -> list[Candidate]:
        """뜻으로 가까운 문서 — 지금 모델의 벡터가 있는 문서 가운데 cosine 유사도가 기준 이상인 것, 가까운 순."""
