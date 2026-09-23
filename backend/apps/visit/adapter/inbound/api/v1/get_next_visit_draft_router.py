from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_next_visit_draft_schema import NextVisitDraftSchema
from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.dependencies.get_next_visit_draft_provider import get_get_next_visit_draft_use_case

get_next_visit_draft_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_next_visit_draft_router.get("/{shop_id}/visits/{visit_id}/next-draft", response_model=NextVisitDraftSchema)
async def get_next_visit_draft(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetNextVisitDraftUseCase = Depends(get_get_next_visit_draft_use_case),
) -> NextVisitDraftSchema:
    return NextVisitDraftSchema.of(
        await use_case.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx, visit_id=visit_id))
    )
