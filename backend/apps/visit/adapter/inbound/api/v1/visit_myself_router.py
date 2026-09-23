from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from visit.adapter.inbound.api.schemas.visit_myself_schema import VisitMyselfResponseSchema
from visit.app.dtos.visit_myself_dto import VisitMyselfQuery
from visit.app.ports.input.visit_myself_use_case import VisitMyselfUseCase
from visit.dependencies.visit_myself_provider import get_visit_myself_use_case

visit_myself_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@visit_myself_router.get(
    "/{shop_id}/visits/myself", response_model=VisitMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: VisitMyselfUseCase = Depends(get_visit_myself_use_case),
) -> VisitMyselfResponseSchema:
    result = await use_case.introduce_myself(VisitMyselfQuery(id=5, name="방문 (visit)"))
    return VisitMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
