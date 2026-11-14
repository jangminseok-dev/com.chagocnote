from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from search.adapter.inbound.api.schemas.search_myself_schema import SearchMyselfResponseSchema
from search.app.dtos.search_myself_dto import SearchMyselfQuery
from search.app.ports.input.search_myself_use_case import SearchMyselfUseCase
from search.dependencies.search_myself_provider import get_search_myself_use_case

search_myself_router = APIRouter(prefix="/v1/shops", tags=["search"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@search_myself_router.get(
    "/{shop_id}/search/myself", response_model=SearchMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: SearchMyselfUseCase = Depends(get_search_myself_use_case),
) -> SearchMyselfResponseSchema:
    result = await use_case.introduce_myself(SearchMyselfQuery(id=9, name="기록 검색 (search)"))
    return SearchMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
