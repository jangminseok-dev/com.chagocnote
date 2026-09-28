from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_visit_report_schema import VisitReportSchema
from visit.adapter.inbound.api.schemas.send_visit_report_schema import SendVisitReportRequestSchema
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
from visit.dependencies.send_visit_report_provider import get_send_visit_report_use_case

send_visit_report_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@send_visit_report_router.put("/{shop_id}/visits/{visit_id}/report", response_model=VisitReportSchema)
async def send_visit_report(
    visit_id: VisitId,
    body: SendVisitReportRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: SendVisitReportUseCase = Depends(get_send_visit_report_use_case),
) -> VisitReportSchema:
    view = await use_case.send_visit_report(
        SendVisitReportCommand(ctx=ctx, visit_id=visit_id, hidden_media_ids=tuple(body.hidden_media_ids))
    )
    return VisitReportSchema.of(view)
