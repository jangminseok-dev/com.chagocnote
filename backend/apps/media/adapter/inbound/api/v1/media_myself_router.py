from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from media.adapter.inbound.api.schemas.media_myself_schema import MediaMyselfResponseSchema
from media.app.dtos.media_myself_dto import MediaMyselfQuery
from media.app.ports.input.media_myself_use_case import MediaMyselfUseCase
from media.dependencies.media_myself_provider import get_media_myself_use_case

media_myself_router = APIRouter(prefix="/v1/shops", tags=["media"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@media_myself_router.get(
    "/{shop_id}/media/myself", response_model=MediaMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: MediaMyselfUseCase = Depends(get_media_myself_use_case),
) -> MediaMyselfResponseSchema:
    result = await use_case.introduce_myself(MediaMyselfQuery(id=6, name="미디어 (media)"))
    return MediaMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
