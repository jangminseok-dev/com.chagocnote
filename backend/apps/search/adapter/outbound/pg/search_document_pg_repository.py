from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from search.adapter.outbound.orm.search_orm import SearchDocumentOrm as _D
from search.app.ports.output.search_document_repository import SearchDocumentRepository
from search.domain.entities.search_document import SearchDocument
from search.domain.services.targets import belongs, target_filter


def _target(scope: str, ref_id: int):
    rule = target_filter(scope)
    clauses = [and_(_D.kind.in_(rule.by_source), _D.source_id == ref_id)]
    if rule.by_pet:
        clauses.append(and_(_D.kind.in_(rule.by_pet), _D.pet_id == ref_id))
    return or_(*clauses)


def _to_entity(row: _D) -> SearchDocument:
    return SearchDocument(
        kind=row.kind, source_id=row.source_id, customer_id=row.customer_id, pet_id=row.pet_id,
        visit_id=row.visit_id, happened_on=row.happened_on, body=row.body,
        embedding=tuple(float(x) for x in row.embedding) if row.embedding is not None else None, model=row.model,
    )


class SearchDocumentPgRepository(SearchDocumentRepository):
    """모든 질의가 ctx.shop_id 로 거른다. 글과 벡터를 로그에 남기지 않는다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_target(self, ctx: ShopContext, scope: str, ref_id: int) -> list[SearchDocument]:
        rows = await self._session.scalars(
            select(_D).where(_D.shop_id == ctx.shop_id, _target(scope, ref_id)).order_by(_D.id)
        )
        return [_to_entity(row) for row in rows]

    async def replace_target(
        self, ctx: ShopContext, scope: str, ref_id: int, documents: list[SearchDocument], now: datetime
    ) -> None:
        if not all(belongs(d, scope, ref_id) for d in documents):
            raise ValueError("그 대상의 문서가 아닙니다.")
        keep = {(d.kind, d.source_id) for d in documents}
        existing = await self._session.execute(
            select(_D.id, _D.kind, _D.source_id).where(_D.shop_id == ctx.shop_id, _target(scope, ref_id))
        )
        gone = [row.id for row in existing if (row.kind, row.source_id) not in keep]
        if gone:
            await self._session.execute(delete(_D).where(_D.shop_id == ctx.shop_id, _D.id.in_(gone)))
        for d in documents:
            values = dict(
                customer_id=d.customer_id, pet_id=d.pet_id, visit_id=d.visit_id, happened_on=d.happened_on,
                body=d.body, embedding=list(d.embedding) if d.embedding is not None else None, model=d.model,
                updated_at=now,
            )
            await self._session.execute(
                insert(_D)
                .values(shop_id=ctx.shop_id, kind=d.kind, source_id=d.source_id, **values)
                .on_conflict_do_update(constraint="uq_search_documents_source", set_=values)
            )

    async def delete_for_customer(self, ctx: ShopContext, customer_id: int) -> None:
        await self._session.execute(delete(_D).where(_D.shop_id == ctx.shop_id, _D.customer_id == customer_id))
