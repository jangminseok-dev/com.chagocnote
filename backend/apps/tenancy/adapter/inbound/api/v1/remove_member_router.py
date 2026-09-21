from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.dependencies.remove_member_provider import get_remove_member_use_case

remove_member_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@remove_member_router.delete("/{shop_id}/members/{member_id}", status_code=204)
async def remove_member(
    member_id: int,
    ctx: ShopContext = Depends(require_permission("member:manage")),
    use_case: RemoveMemberUseCase = Depends(get_remove_member_use_case),
) -> None:
    await use_case.remove(RemoveMemberCommand(ctx=ctx, member_id=member_id))
