from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import FormId
from customer.app.dtos.revoke_form_dto import RevokeFormCommand
from customer.app.ports.input.revoke_form_use_case import RevokeFormUseCase
from customer.dependencies.revoke_form_provider import get_revoke_form_use_case
from hub.app.dtos.shop_context import ShopContext

revoke_form_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@revoke_form_router.delete("/{shop_id}/forms/{form_id}", status_code=204)
async def revoke_form(
    form_id: FormId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: RevokeFormUseCase = Depends(get_revoke_form_use_case),
) -> Response:
    await use_case.revoke_form(RevokeFormCommand(ctx=ctx, form_id=form_id))
    return Response(status_code=204)
