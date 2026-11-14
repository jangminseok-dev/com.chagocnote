from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from search.adapter.inbound.api.schemas.search_records_schema import SearchResultSchema
from search.app.dtos.search_records_dto import SearchRecordsQuery
from search.app.ports.input.search_records_use_case import SearchRecordsUseCase
from search.dependencies.search_records_provider import get_search_records_use_case

search_records_router = APIRouter(prefix="/v1/shops", tags=["search"])

# 받는 글자 수의 바깥 한계 — 다듬은 뒤의 2~100자는 유스케이스가 본다(공백을 줄인 뒤의 길이라 여기서 못 본다).
_RAW_MAX = 500


@search_records_router.get("/{shop_id}/search", response_model=SearchResultSchema)
async def search_records(
    q: str = Query(max_length=_RAW_MAX),
    pet_id: int | None = Query(default=None, ge=1),
    ctx: ShopContext = Depends(get_shop_context),
    use_case: SearchRecordsUseCase = Depends(get_search_records_use_case),
) -> SearchResultSchema:
    """매장이 적어 둔 글에서 찾는다(매장 멤버). 검색어는 접근 로그에서 가려진다(core/access_log)."""
    return SearchResultSchema.of(await use_case.search_records(SearchRecordsQuery(ctx=ctx, q=q, pet_id=pet_id)))
