from fastapi import APIRouter, Depends

from platform_admin.adapter.inbound.api.schemas.platform_myself_schema import (
    PlatformMyselfResponseSchema,
)
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.dependencies.operator_guard import require_operator
from platform_admin.dependencies.platform_myself_provider import get_platform_myself_use_case

platform_myself_router = APIRouter(
    prefix="/v1/platform", tags=["platform"], dependencies=[Depends(require_operator)]
)


@platform_myself_router.get("/myself", response_model=PlatformMyselfResponseSchema)
async def introduce_myself(
    use_case: PlatformMyselfUseCase = Depends(get_platform_myself_use_case),
) -> PlatformMyselfResponseSchema:
    result = await use_case.introduce_myself(
        PlatformMyselfQuery(id=3, name="플랫폼 운영 (platform_admin)")
    )
    return PlatformMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
