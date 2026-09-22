from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.dependencies.delete_customer_provider import get_delete_customer_use_case
from hub.app.dtos.shop_context import ShopContext

delete_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@delete_customer_router.delete("/{shop_id}/customers/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: CustomerId,
    ctx: ShopContext = Depends(require_permission("customer:delete")),
    use_case: DeleteCustomerUseCase = Depends(get_delete_customer_use_case),
) -> Response:
    await use_case.delete_customer(DeleteCustomerCommand(ctx=ctx, customer_id=customer_id))
    return Response(status_code=204)
