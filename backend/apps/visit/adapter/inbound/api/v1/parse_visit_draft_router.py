from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.parse_visit_draft_schema import (
    VisitDraftRequestSchema,
    VisitDraftSchema,
)
from visit.app.dtos.parse_visit_draft_dto import ParseVisitDraftCommand
from visit.app.ports.input.parse_visit_draft_use_case import ParseVisitDraftUseCase
from visit.dependencies.parse_visit_draft_provider import get_parse_visit_draft_use_case

parse_visit_draft_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@parse_visit_draft_router.post("/{shop_id}/visit-drafts", response_model=VisitDraftSchema)
async def parse_visit_draft(
    body: VisitDraftRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: ParseVisitDraftUseCase = Depends(get_parse_visit_draft_use_case),
) -> VisitDraftSchema:
    """카톡 글 → 예약 초안. 저장하지 않는다(사람이 확인한 뒤 POST /visits 로 저장)."""
    return VisitDraftSchema.of(await use_case.parse_visit_draft(ParseVisitDraftCommand(ctx=ctx, text=body.text)))
