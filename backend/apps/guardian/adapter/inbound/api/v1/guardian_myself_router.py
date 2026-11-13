from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from guardian.adapter.inbound.api.schemas.guardian_myself_schema import GuardianMyselfResponseSchema
from guardian.app.dtos.guardian_myself_dto import GuardianMyselfQuery
from guardian.app.ports.input.guardian_myself_use_case import GuardianMyselfUseCase
from guardian.dependencies.guardian_myself_provider import get_guardian_myself_use_case

guardian_myself_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])


# 보호자는 매장의 멤버가 아니다 — 로그인만 확인한다(로그인 없이 열리는 경로를 늘리지 않는다).
@guardian_myself_router.get(
    "/myself", response_model=GuardianMyselfResponseSchema, dependencies=[Depends(get_current_user_id)],
)
async def introduce_myself(
    use_case: GuardianMyselfUseCase = Depends(get_guardian_myself_use_case),
) -> GuardianMyselfResponseSchema:
    result = await use_case.introduce_myself(GuardianMyselfQuery(id=8, name="보호자 (guardian)"))
    return GuardianMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
