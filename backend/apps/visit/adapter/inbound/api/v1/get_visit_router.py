from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_visit_schema import VisitDetailSchema
from visit.app.dtos.get_visit_dto import GetVisitQuery
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.dependencies.get_visit_provider import get_get_visit_use_case

get_visit_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_router.get("/{shop_id}/visits/{visit_id}", response_model=VisitDetailSchema)
async def get_visit(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitUseCase = Depends(get_get_visit_use_case),
) -> VisitDetailSchema:
    return VisitDetailSchema.of(await use_case.get_visit(GetVisitQuery(ctx=ctx, visit_id=visit_id)))
