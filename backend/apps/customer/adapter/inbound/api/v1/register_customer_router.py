from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.adapter.inbound.api.schemas.register_customer_schema import (
    RegisterCustomerRequestSchema,
)
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.dependencies.register_customer_provider import get_register_customer_use_case
from hub.app.dtos.shop_context import ShopContext

register_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@register_customer_router.post(
    "/{shop_id}/customers", response_model=CustomerDetailSchema, status_code=201
)
async def register_customer(
    body: RegisterCustomerRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: RegisterCustomerUseCase = Depends(get_register_customer_use_case),
) -> CustomerDetailSchema:
    view = await use_case.register_customer(
        RegisterCustomerCommand(ctx=ctx, customer=body.customer.to_input(), pet=body.pet.to_input(),
                                intake_answer_id=body.intake_answer_id)
    )
    return CustomerDetailSchema.of(view)
