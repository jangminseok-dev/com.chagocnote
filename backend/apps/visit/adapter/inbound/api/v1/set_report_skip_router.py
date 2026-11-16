from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.app.dtos.set_report_skip_dto import SetReportSkipCommand
from visit.app.ports.input.set_report_skip_use_case import SetReportSkipUseCase
from visit.dependencies.set_report_skip_provider import get_set_report_skip_use_case

set_report_skip_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 알림장을 보내는 사람과 같은 권한이다(record:write) — 하루 마무리의 [보내지 않음], 방문 상세의 되돌리기(⑬).
@set_report_skip_router.put("/{shop_id}/visits/{visit_id}/report-skip", status_code=204)
async def skip_visit_report(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: SetReportSkipUseCase = Depends(get_set_report_skip_use_case),
) -> Response:
    await use_case.set_report_skip(SetReportSkipCommand(ctx=ctx, visit_id=visit_id, skip=True))
    return Response(status_code=204)


@set_report_skip_router.delete("/{shop_id}/visits/{visit_id}/report-skip", status_code=204)
async def unskip_visit_report(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: SetReportSkipUseCase = Depends(get_set_report_skip_use_case),
) -> Response:
    await use_case.set_report_skip(SetReportSkipCommand(ctx=ctx, visit_id=visit_id, skip=False))
    return Response(status_code=204)
