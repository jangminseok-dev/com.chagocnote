from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from media.adapter.inbound.api.path_params import MediaId
from media.adapter.inbound.api.schemas.media_schema import MediaSchema
from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.ports.input.confirm_upload_use_case import ConfirmUploadUseCase
from media.dependencies.confirm_upload_provider import get_confirm_upload_use_case

confirm_upload_router = APIRouter(prefix="/v1/shops", tags=["media"])


@confirm_upload_router.post("/{shop_id}/media/{media_id}/confirm", response_model=MediaSchema)
async def confirm_upload(
    media_id: MediaId,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: ConfirmUploadUseCase = Depends(get_confirm_upload_use_case),
) -> MediaSchema:
    return MediaSchema.of(await use_case.confirm_upload(ConfirmUploadCommand(ctx=ctx, media_id=media_id)))
