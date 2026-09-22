from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.adapter.inbound.api.schemas.update_customer_schema import UpdateCustomerRequestSchema
from customer.app.dtos.update_customer_dto import UpdateCustomerCommand
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.dependencies.update_customer_provider import get_update_customer_use_case
from hub.app.dtos.shop_context import ShopContext

update_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@update_customer_router.put("/{shop_id}/customers/{customer_id}", response_model=CustomerDetailSchema)
async def update_customer(
    customer_id: CustomerId,
    body: UpdateCustomerRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: UpdateCustomerUseCase = Depends(get_update_customer_use_case),
) -> CustomerDetailSchema:
    view = await use_case.update_customer(
        UpdateCustomerCommand(ctx=ctx, customer_id=customer_id, customer=body.to_input())
    )
    return CustomerDetailSchema.of(view)
