from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.put_visit_record_schema import PutVisitRecordRequestSchema
from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.ports.input.put_visit_record_use_case import PutVisitRecordUseCase
from visit.dependencies.put_visit_record_provider import get_put_visit_record_use_case

put_visit_record_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@put_visit_record_router.put("/{shop_id}/visits/{visit_id}/record", response_model=RecordSchema)
async def put_visit_record(
    visit_id: VisitId,
    body: PutVisitRecordRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: PutVisitRecordUseCase = Depends(get_put_visit_record_use_case),
) -> RecordSchema:
    view = await use_case.put_visit_record(
        PutVisitRecordCommand(ctx=ctx, visit_id=visit_id, version=body.version, record=body.to_input())
    )
    return RecordSchema.of(view)
