from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import AfterValidator

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.list_customers_schema import CustomerListSchema
from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.app.dtos.list_customers_dto import ListCustomersQuery
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.dependencies.list_customers_provider import get_list_customers_use_case
from hub.app.dtos.shop_context import ShopContext

list_customers_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@list_customers_router.get("/{shop_id}/customers", response_model=CustomerListSchema)
async def list_customers(
    q: Annotated[str | None, Query(max_length=50), AfterValidator(reject_control_chars)] = None,
    sort: Literal["recent", "name"] = "recent",
    include_passed: bool = False,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListCustomersUseCase = Depends(get_list_customers_use_case),
) -> CustomerListSchema:
    view = await use_case.list_customers(
        ListCustomersQuery(ctx=ctx, q=q, sort=sort, include_passed=include_passed, cursor=cursor)
    )
    return CustomerListSchema.of(view)
