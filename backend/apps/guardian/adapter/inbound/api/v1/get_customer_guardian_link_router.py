from typing import Annotated

from fastapi import APIRouter, Depends, Path

from core.shop_guard import get_shop_context
from guardian.adapter.inbound.api.schemas.guardian_link_schema import CustomerGuardianLinkSchema
from guardian.app.dtos.get_customer_guardian_link_dto import GetCustomerGuardianLinkQuery
from guardian.app.ports.input.get_customer_guardian_link_use_case import GetCustomerGuardianLinkUseCase
from guardian.dependencies.get_customer_guardian_link_provider import get_get_customer_guardian_link_use_case
from hub.app.dtos.shop_context import ShopContext

get_customer_guardian_link_router = APIRouter(prefix="/v1/shops", tags=["guardian"])


@get_customer_guardian_link_router.get(
    "/{shop_id}/customers/{customer_id}/guardian-link", response_model=CustomerGuardianLinkSchema,
)
async def get_customer_guardian_link(
    customer_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetCustomerGuardianLinkUseCase = Depends(get_get_customer_guardian_link_use_case),
) -> CustomerGuardianLinkSchema:
    view = await use_case.get_link(GetCustomerGuardianLinkQuery(ctx=ctx, customer_id=customer_id))
    return CustomerGuardianLinkSchema(linked=view.linked, linked_at=view.linked_at)
