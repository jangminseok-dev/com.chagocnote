from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from platform_admin.adapter.inbound.api.schemas.platform_myself_schema import (
    PlatformMyselfResponseSchema,
)
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.dependencies.platform_myself_provider import get_platform_myself_use_case

platform_myself_router = APIRouter(prefix="/v1/platform", tags=["platform"])


@platform_myself_router.get("/myself", response_model=PlatformMyselfResponseSchema)
async def introduce_myself(
    user_id: int = Depends(get_current_user_id),
    use_case: PlatformMyselfUseCase = Depends(get_platform_myself_use_case),
) -> PlatformMyselfResponseSchema:
    result = await use_case.introduce_myself(
        PlatformMyselfQuery(id=3, name="플랫폼 운영 (platform_admin)", user_id=user_id)
    )
    return PlatformMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
