from datetime import date

from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_day_visits_schema import DayVisitsSchema
from visit.app.dtos.list_day_visits_dto import ListDayVisitsQuery
from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
from visit.dependencies.list_day_visits_provider import get_list_day_visits_use_case

list_day_visits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_day_visits_router.get("/{shop_id}/visits", response_model=DayVisitsSchema)
async def list_day_visits(
    date: date,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListDayVisitsUseCase = Depends(get_list_day_visits_use_case),
) -> DayVisitsSchema:
    return DayVisitsSchema.of(await use_case.list_day_visits(ListDayVisitsQuery(ctx=ctx, day=date)))
