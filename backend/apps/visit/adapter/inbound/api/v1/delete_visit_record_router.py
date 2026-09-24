from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.dependencies.delete_visit_record_provider import get_delete_visit_record_use_case

delete_visit_record_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 기록 삭제는 record:delete(사장)다 — 사진 한 장 빼기는 전체 교체(record:write)로 한다.
@delete_visit_record_router.delete("/{shop_id}/visits/{visit_id}/record", status_code=204)
async def delete_visit_record(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("record:delete")),
    use_case: DeleteVisitRecordUseCase = Depends(get_delete_visit_record_use_case),
) -> Response:
    await use_case.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx, visit_id=visit_id))
    return Response(status_code=204)
