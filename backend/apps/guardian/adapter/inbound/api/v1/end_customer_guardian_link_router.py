from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from core.shop_guard import require_permission
from guardian.app.dtos.end_customer_guardian_link_dto import EndCustomerGuardianLinkCommand
from guardian.app.ports.input.end_customer_guardian_link_use_case import EndCustomerGuardianLinkUseCase
from guardian.dependencies.end_customer_guardian_link_provider import get_end_customer_guardian_link_use_case
from hub.app.dtos.shop_context import ShopContext

end_customer_guardian_link_router = APIRouter(prefix="/v1/shops", tags=["guardian"])


@end_customer_guardian_link_router.delete("/{shop_id}/customers/{customer_id}/guardian-link", status_code=204)
async def end_customer_guardian_link(
    customer_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: EndCustomerGuardianLinkUseCase = Depends(get_end_customer_guardian_link_use_case),
) -> Response:
    await use_case.end_link(EndCustomerGuardianLinkCommand(ctx=ctx, customer_id=customer_id))
    return Response(status_code=204)
