from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.create_invite_schema import CreateInviteResponseSchema
from tenancy.app.dtos.create_invite_dto import CreateInviteCommand
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.dependencies.create_invite_provider import get_create_invite_use_case

create_invite_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@create_invite_router.post(
    "/{shop_id}/invites", response_model=CreateInviteResponseSchema, status_code=201
)
async def create_invite(
    ctx: ShopContext = Depends(require_permission("member:manage")),
    use_case: CreateInviteUseCase = Depends(get_create_invite_use_case),
) -> CreateInviteResponseSchema:
    invite = await use_case.create(CreateInviteCommand(ctx=ctx))
    return CreateInviteResponseSchema(code=invite.code, role=invite.role, expires_at=invite.expires_at)
