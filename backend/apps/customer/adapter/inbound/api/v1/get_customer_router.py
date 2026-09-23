from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerOverviewSchema
from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.dependencies.get_customer_provider import get_get_customer_use_case
from hub.app.dtos.shop_context import ShopContext

get_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@get_customer_router.get("/{shop_id}/customers/{customer_id}", response_model=CustomerOverviewSchema)
async def get_customer(
    customer_id: CustomerId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetCustomerUseCase = Depends(get_get_customer_use_case),
) -> CustomerOverviewSchema:
    return CustomerOverviewSchema.of(
        await use_case.get_customer(GetCustomerQuery(ctx=ctx, customer_id=customer_id))
    )
