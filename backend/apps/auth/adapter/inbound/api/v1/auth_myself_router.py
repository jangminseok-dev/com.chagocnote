from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.auth_myself_schema import AuthMyselfResponseSchema
from auth.app.dtos.auth_myself_dto import AuthMyselfQuery
from auth.app.ports.input.auth_myself_use_case import AuthMyselfUseCase
from auth.dependencies.auth_myself_provider import get_auth_myself_use_case

auth_myself_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@auth_myself_router.get("/myself", response_model=AuthMyselfResponseSchema)
async def introduce_myself(
    use_case: AuthMyselfUseCase = Depends(get_auth_myself_use_case),
) -> AuthMyselfResponseSchema:
    result = await use_case.introduce_myself(AuthMyselfQuery(id=1, name="인증 (auth)"))
    return AuthMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
