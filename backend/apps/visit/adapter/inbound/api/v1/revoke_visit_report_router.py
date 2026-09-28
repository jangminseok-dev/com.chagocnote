from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
from visit.dependencies.revoke_visit_report_provider import get_revoke_visit_report_use_case

revoke_visit_report_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 끊기는 보내기와 같은 권한이다(record:write, 사장·직원) — 잘못 보낸 링크를 보낸 사람이 바로 끊을 수 있게.
@revoke_visit_report_router.delete("/{shop_id}/visits/{visit_id}/report", status_code=204)
async def revoke_visit_report(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: RevokeVisitReportUseCase = Depends(get_revoke_visit_report_use_case),
) -> Response:
    await use_case.revoke_visit_report(RevokeVisitReportCommand(ctx=ctx, visit_id=visit_id))
    return Response(status_code=204)
