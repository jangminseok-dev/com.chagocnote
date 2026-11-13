from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.app.dtos.clear_customer_caution_dto import ClearCustomerCautionCommand
from customer.app.ports.input.clear_customer_caution_use_case import ClearCustomerCautionUseCase
from customer.dependencies.clear_customer_caution_provider import get_clear_customer_caution_use_case
from hub.app.dtos.shop_context import ShopContext

clear_customer_caution_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@clear_customer_caution_router.delete("/{shop_id}/customers/{customer_id}/caution", response_model=CustomerDetailSchema)
async def clear_customer_caution(
    customer_id: CustomerId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: ClearCustomerCautionUseCase = Depends(get_clear_customer_caution_use_case),
) -> CustomerDetailSchema:
    view = await use_case.clear_customer_caution(ClearCustomerCautionCommand(ctx=ctx, customer_id=customer_id))
    return CustomerDetailSchema.of(view)
