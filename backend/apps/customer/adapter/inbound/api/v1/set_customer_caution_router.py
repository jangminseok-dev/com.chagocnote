from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.adapter.inbound.api.schemas.set_customer_caution_schema import SetCustomerCautionRequestSchema
from customer.app.dtos.set_customer_caution_dto import SetCustomerCautionCommand
from customer.app.ports.input.set_customer_caution_use_case import SetCustomerCautionUseCase
from customer.dependencies.set_customer_caution_provider import get_set_customer_caution_use_case
from hub.app.dtos.shop_context import ShopContext

set_customer_caution_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@set_customer_caution_router.put("/{shop_id}/customers/{customer_id}/caution", response_model=CustomerDetailSchema)
async def set_customer_caution(
    customer_id: CustomerId,
    body: SetCustomerCautionRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: SetCustomerCautionUseCase = Depends(get_set_customer_caution_use_case),
) -> CustomerDetailSchema:
    view = await use_case.set_customer_caution(SetCustomerCautionCommand(ctx=ctx, customer_id=customer_id, reason=body.reason))
    return CustomerDetailSchema.of(view)
