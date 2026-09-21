from typing import Annotated

from fastapi import APIRouter, Depends, Path

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.change_member_role_schema import (
    ChangedMemberResponseSchema,
    ChangeMemberRoleRequestSchema,
)
from tenancy.app.dtos.change_member_role_dto import ChangeMemberRoleCommand
from tenancy.app.ports.input.change_member_role_use_case import ChangeMemberRoleUseCase
from tenancy.dependencies.change_member_role_provider import get_change_member_role_use_case

change_member_role_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@change_member_role_router.patch(
    "/{shop_id}/members/{member_id}", response_model=ChangedMemberResponseSchema
)
async def change_member_role(
    member_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    body: ChangeMemberRoleRequestSchema,
    ctx: ShopContext = Depends(require_permission("member:manage")),
    use_case: ChangeMemberRoleUseCase = Depends(get_change_member_role_use_case),
) -> ChangedMemberResponseSchema:
    changed = await use_case.change_role(
        ChangeMemberRoleCommand(ctx=ctx, member_id=member_id, role=body.role)
    )
    return ChangedMemberResponseSchema(
        member_id=changed.member_id, user_id=changed.user_id, role=changed.role
    )
