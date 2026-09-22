from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AfterValidator

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.lookup_customer_schema import (
    LookupCustomerResponseSchema,
)
from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery
from customer.app.ports.input.lookup_customer_use_case import LookupCustomerUseCase
from customer.dependencies.lookup_customer_provider import get_lookup_customer_use_case
from hub.app.dtos.shop_context import ShopContext

lookup_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@lookup_customer_router.get("/{shop_id}/customers/lookup", response_model=LookupCustomerResponseSchema)
async def lookup_customer(
    phone: Annotated[str, Query(min_length=1, max_length=20), AfterValidator(reject_control_chars)],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: LookupCustomerUseCase = Depends(get_lookup_customer_use_case),
) -> LookupCustomerResponseSchema:
    result = await use_case.lookup_customer(LookupCustomerQuery(ctx=ctx, phone=phone))
    return LookupCustomerResponseSchema(
        customer_id=result.customer_id, name=result.name, pet_names=result.pet_names
    )
