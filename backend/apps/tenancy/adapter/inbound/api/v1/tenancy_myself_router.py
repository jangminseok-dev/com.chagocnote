from fastapi import APIRouter, Depends

from tenancy.adapter.inbound.api.schemas.tenancy_myself_schema import TenancyMyselfResponseSchema
from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery
from tenancy.app.ports.input.tenancy_myself_use_case import TenancyMyselfUseCase
from tenancy.dependencies.tenancy_myself_provider import get_tenancy_myself_use_case

tenancy_myself_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@tenancy_myself_router.get("/myself", response_model=TenancyMyselfResponseSchema)
async def introduce_myself(
    use_case: TenancyMyselfUseCase = Depends(get_tenancy_myself_use_case),
) -> TenancyMyselfResponseSchema:
    result = await use_case.introduce_myself(TenancyMyselfQuery(id=2, name="매장 (tenancy)"))
    return TenancyMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
