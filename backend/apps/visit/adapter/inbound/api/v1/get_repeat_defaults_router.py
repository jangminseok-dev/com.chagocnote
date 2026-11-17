from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_repeat_defaults_schema import RepeatDefaultsSchema
from visit.app.dtos.get_repeat_defaults_dto import GetRepeatDefaultsQuery
from visit.app.ports.input.get_repeat_defaults_use_case import GetRepeatDefaultsUseCase
from visit.dependencies.get_repeat_defaults_provider import get_get_repeat_defaults_use_case

get_repeat_defaults_router = APIRouter(prefix="/v1/shops", tags=["visits"])

_MAX_BIGINT = 9_223_372_036_854_775_807
_Id = Annotated[int, Query(ge=1, le=_MAX_BIGINT)]


@get_repeat_defaults_router.get("/{shop_id}/visits/repeat-defaults", response_model=RepeatDefaultsSchema)
async def get_repeat_defaults(
    customer_id: _Id,
    # 같은 이름을 되풀이해 여러 마리를 준다(?pet_ids=1&pet_ids=2). 없으면 보호자만의 예약이다.
    pet_ids: Annotated[list[Annotated[int, Query(ge=1, le=_MAX_BIGINT)]], Query(max_length=10)] = [],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetRepeatDefaultsUseCase = Depends(get_get_repeat_defaults_use_case),
) -> RepeatDefaultsSchema:
    view = await use_case.get_repeat_defaults(
        GetRepeatDefaultsQuery(ctx=ctx, customer_id=customer_id, pet_ids=tuple(dict.fromkeys(pet_ids))))
    return RepeatDefaultsSchema.of(view)
