from __future__ import annotations

from hub.app.dtos.search_source import SourceDocument
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.search_source_port import SearchSourcePort
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.search_documents import visit_documents
from visit.domain.errors import VisitNotFoundError


class VisitSearchSourceInteractor(SearchSourcePort):
    """허브의 SearchSourcePort 구현 — scope "visit" 만 답한다(HTTP 표면 없음). 색인기가 요청 밖에서 부른다.

    잠그지 않는다. 익명화한 고객의 방문은 메모가 이미 비어 있어(`clear_customer_memos`) 문서가 없다."""

    def __init__(self, visits: VisitLookupRepository, records: VisitRecordRepository) -> None:
        self._visits = visits
        self._records = records

    async def documents(self, ctx: ShopContext, scope: str, ref_id: int) -> list[SourceDocument]:
        if scope != "visit":
            return []
        try:
            visit = await self._visits.get(ctx, ref_id)
        except VisitNotFoundError:
            return []
        return visit_documents(visit, await self._records.get(ctx, ref_id), ctx.timezone)
