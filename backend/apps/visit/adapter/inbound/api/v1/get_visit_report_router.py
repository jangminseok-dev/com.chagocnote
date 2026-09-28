from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_visit_report_schema import VisitReportSchema
from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery
from visit.app.ports.input.get_visit_report_use_case import GetVisitReportUseCase
from visit.dependencies.get_visit_report_provider import get_get_visit_report_use_case

get_visit_report_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_report_router.get("/{shop_id}/visits/{visit_id}/report", response_model=VisitReportSchema)
async def get_visit_report(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitReportUseCase = Depends(get_get_visit_report_use_case),
) -> VisitReportSchema:
    return VisitReportSchema.of(await use_case.get_visit_report(GetVisitReportQuery(ctx=ctx, visit_id=visit_id)))
