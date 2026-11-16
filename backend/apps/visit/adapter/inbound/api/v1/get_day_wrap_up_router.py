from datetime import date

from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_day_wrap_up_schema import DayWrapUpSchema
from visit.app.dtos.get_day_wrap_up_dto import GetDayWrapUpQuery
from visit.app.ports.input.get_day_wrap_up_use_case import GetDayWrapUpUseCase
from visit.dependencies.get_day_wrap_up_provider import get_get_day_wrap_up_use_case

get_day_wrap_up_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 매장 멤버 — 장의 종류는 그 장을 끝내는 권한(reservation:write·sales:write·record:write)이 있을 때만 나온다.
@get_day_wrap_up_router.get("/{shop_id}/days/{day}/wrap-up", response_model=DayWrapUpSchema)
async def get_day_wrap_up(
    day: date,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetDayWrapUpUseCase = Depends(get_get_day_wrap_up_use_case),
) -> DayWrapUpSchema:
    return DayWrapUpSchema.of(await use_case.get_day_wrap_up(GetDayWrapUpQuery(ctx=ctx, day=day)))
