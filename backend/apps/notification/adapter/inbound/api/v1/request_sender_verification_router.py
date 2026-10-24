from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.request_sender_verification_schema import (
    RequestSenderVerificationRequestSchema,
    SenderVerificationRequestedSchema,
)
from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand
from notification.app.ports.input.request_sender_verification_use_case import RequestSenderVerificationUseCase
from notification.dependencies.request_sender_verification_provider import (
    get_request_sender_verification_use_case,
)

request_sender_verification_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@request_sender_verification_router.post(
    "/{shop_id}/notification/sender/verification", status_code=202,
    response_model=SenderVerificationRequestedSchema,
)
async def request_sender_verification(
    body: RequestSenderVerificationRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: RequestSenderVerificationUseCase = Depends(get_request_sender_verification_use_case),
) -> SenderVerificationRequestedSchema:
    await use_case.request_sender_verification(RequestSenderVerificationCommand(ctx=ctx, phone=body.phone))
    return SenderVerificationRequestedSchema()
