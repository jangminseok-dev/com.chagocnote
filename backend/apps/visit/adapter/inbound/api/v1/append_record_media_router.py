from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.append_record_media_schema import AppendRecordMediaRequestSchema
from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.ports.input.append_record_media_use_case import AppendRecordMediaUseCase
from visit.dependencies.append_record_media_provider import get_append_record_media_use_case

append_record_media_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@append_record_media_router.post("/{shop_id}/visits/{visit_id}/record/media", response_model=RecordSchema)
async def append_record_media(
    visit_id: VisitId,
    body: AppendRecordMediaRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: AppendRecordMediaUseCase = Depends(get_append_record_media_use_case),
) -> RecordSchema:
    view = await use_case.append_record_media(
        AppendRecordMediaCommand(ctx=ctx, visit_id=visit_id, media_id=body.media_id, phase=body.phase)
    )
    return RecordSchema.of(view)
