from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from tenancy.adapter.inbound.api.schemas.accept_invite_schema import (
    AcceptInviteRequestSchema,
    AcceptInviteResponseSchema,
)
from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.dependencies.accept_invite_provider import get_accept_invite_use_case

accept_invite_router = APIRouter(prefix="/v1/invites", tags=["invites"])


@accept_invite_router.post("/accept", response_model=AcceptInviteResponseSchema)
async def accept_invite(
    body: AcceptInviteRequestSchema,
    user_id: int = Depends(get_current_user_id),
    use_case: AcceptInviteUseCase = Depends(get_accept_invite_use_case),
) -> AcceptInviteResponseSchema:
    result = await use_case.accept(AcceptInviteCommand(user_id=user_id, code=body.code))
    return AcceptInviteResponseSchema(
        shop_id=result.shop_id, shop_name=result.shop_name,
        role=result.role, member_id=result.member_id,
    )
