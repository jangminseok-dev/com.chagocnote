from fastapi import APIRouter, Depends

from platform_admin.adapter.inbound.api.schemas.create_shop_schema import (
    CreateShopRequestSchema,
    CreateShopResponseSchema,
)
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase
from platform_admin.dependencies.create_shop_provider import get_create_shop_use_case
from platform_admin.dependencies.operator_guard import require_operator

create_shop_router = APIRouter(
    prefix="/v1/platform", tags=["platform"], dependencies=[Depends(require_operator)]
)


@create_shop_router.post("/shops", response_model=CreateShopResponseSchema, status_code=201)
async def create_shop(
    body: CreateShopRequestSchema,
    use_case: CreateShopUseCase = Depends(get_create_shop_use_case),
) -> CreateShopResponseSchema:
    shop = await use_case.create_shop(
        CreateShopCommand(name=body.name, business_type=body.business_type)
    )
    return CreateShopResponseSchema(
        shop_id=shop.shop_id,
        name=shop.name,
        owner_invite_code=shop.owner_invite_code,
        invite_expires_at=shop.invite_expires_at,
    )
