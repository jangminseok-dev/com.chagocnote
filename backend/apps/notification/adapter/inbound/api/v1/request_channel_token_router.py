from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.request_channel_token_schema import (
    ChannelTokenRequestedSchema,
    RequestChannelTokenRequestSchema,
)
from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand
from notification.app.ports.input.request_channel_token_use_case import RequestChannelTokenUseCase
from notification.dependencies.request_channel_token_provider import get_request_channel_token_use_case

request_channel_token_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@request_channel_token_router.post(
    "/{shop_id}/notification/channel/token", status_code=202, response_model=ChannelTokenRequestedSchema,
)
async def request_channel_token(
    body: RequestChannelTokenRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: RequestChannelTokenUseCase = Depends(get_request_channel_token_use_case),
) -> ChannelTokenRequestedSchema:
    await use_case.request_channel_token(RequestChannelTokenCommand(
        ctx=ctx, search_id=body.search_id, admin_phone=body.admin_phone, category_code=body.category_code))
    return ChannelTokenRequestedSchema()
