from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from search.adapter.outbound.orm.search_orm import SearchDocumentOrm as _D
from search.app.ports.output.search_candidate_repository import SearchCandidateRepository
from search.domain.entities.search_document import Candidate, PetScope
from search.domain.services.embedding_model import CURRENT_MODEL
from search.domain.services.rank_fusion import (
    CANDIDATE_LIMIT,
    LEXICAL_MIN_SIMILARITY,
    SEMANTIC_MIN_SIMILARITY,
)

_COLUMNS = (_D.id, _D.kind, _D.source_id, _D.customer_id, _D.pet_id, _D.visit_id, _D.happened_on, _D.body)


def _within(ctx: ShopContext, pet_scope: PetScope | None) -> list:
    """모든 질의의 바탕 — 이 매장의 문서만. 아이로 좁히면 그 아이의 문서와 그 아이 보호자의 메모만."""
    clauses = [_D.shop_id == ctx.shop_id]
    if pet_scope is not None:
        clauses.append(or_(
            _D.pet_id == pet_scope.pet_id,
            and_(_D.kind == "customer_memo", _D.customer_id == pet_scope.customer_id),
        ))
    return clauses


def _candidates(rows) -> list[Candidate]:
    return [
        Candidate(id=r.id, kind=r.kind, source_id=r.source_id, customer_id=r.customer_id, pet_id=r.pet_id,
                  visit_id=r.visit_id, happened_on=r.happened_on, body=r.body)
        for r in rows
    ]


class SearchCandidatePgRepository(SearchCandidateRepository):
    """값은 전부 바인딩한다. 검색어·글·벡터를 로그에 남기지 않는다(엔진은 hide_parameters 다)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lexical(
        self, ctx: ShopContext, q: str, pattern: str, pet_scope: PetScope | None, limit: int = CANDIDATE_LIMIT
    ) -> list[Candidate]:
        contains = _D.body.ilike(pattern, escape="\\")
        similarity = func.word_similarity(q, _D.body)   # 검색어가 글의 한 토막과 얼마나 닮았나(pg_trgm)
        rows = await self._session.execute(
            select(*_COLUMNS)
            .where(*_within(ctx, pet_scope), or_(contains, similarity >= LEXICAL_MIN_SIMILARITY))
            .order_by(contains.desc(), similarity.desc(), _D.happened_on.desc().nulls_last(), _D.id.desc())
            .limit(limit)
        )
        return _candidates(rows)

    async def semantic(
        self, ctx: ShopContext, vector: tuple[float, ...], pet_scope: PetScope | None, limit: int = CANDIDATE_LIMIT
    ) -> list[Candidate]:
        distance = _D.embedding.cosine_distance(list(vector))
        rows = await self._session.execute(
            select(*_COLUMNS)
            .where(
                *_within(ctx, pet_scope), _D.embedding.is_not(None), _D.model == CURRENT_MODEL,
                distance <= 1 - SEMANTIC_MIN_SIMILARITY,
            )
            .order_by(distance, _D.id.desc())
            .limit(limit)
        )
        return _candidates(rows)
