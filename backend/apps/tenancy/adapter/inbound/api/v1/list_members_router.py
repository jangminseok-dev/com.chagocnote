from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.list_members_schema import MemberSchema
from tenancy.app.dtos.list_members_dto import ListMembersQuery
from tenancy.app.ports.input.list_members_use_case import ListMembersUseCase
from tenancy.dependencies.list_members_provider import get_list_members_use_case

list_members_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@list_members_router.get("/{shop_id}/members", response_model=list[MemberSchema])
async def list_members(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListMembersUseCase = Depends(get_list_members_use_case),
) -> list[MemberSchema]:
    views = await use_case.list_members(ListMembersQuery(ctx=ctx))
    return [
        MemberSchema(
            member_id=v.member_id, user_id=v.user_id, display_name=v.display_name,
            profile_image_url=v.profile_image_url, role=v.role, joined_at=v.joined_at,
        )
        for v in views
    ]
