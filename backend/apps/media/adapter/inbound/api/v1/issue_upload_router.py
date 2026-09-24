from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from media.adapter.inbound.api.schemas.issue_upload_schema import IssuedUploadSchema, IssueUploadRequestSchema
from media.app.dtos.issue_upload_dto import IssueUploadCommand
from media.app.ports.input.issue_upload_use_case import IssueUploadUseCase
from media.dependencies.issue_upload_provider import get_issue_upload_use_case

issue_upload_router = APIRouter(prefix="/v1/shops", tags=["media"])


@issue_upload_router.post("/{shop_id}/media/uploads", response_model=IssuedUploadSchema, status_code=201)
async def issue_upload(
    body: IssueUploadRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: IssueUploadUseCase = Depends(get_issue_upload_use_case),
) -> IssuedUploadSchema:
    view = await use_case.issue_upload(IssueUploadCommand(
        ctx=ctx, kind=body.kind, content_type=body.content_type, byte_size=body.byte_size, width=body.width,
        height=body.height, duration_seconds=body.duration_seconds,
    ))
    return IssuedUploadSchema.of(view)
