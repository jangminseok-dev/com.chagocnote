from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_closed_dates_schema import (
    ClosedDateListSchema,
    ClosedDateSchema,
)
from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.ports.input.list_closed_dates_use_case import ListClosedDatesUseCase
from visit.dependencies.list_closed_dates_provider import get_list_closed_dates_use_case

list_closed_dates_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_closed_dates_router.get("/{shop_id}/closed-dates", response_model=ClosedDateListSchema)
async def list_closed_dates(
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListClosedDatesUseCase = Depends(get_list_closed_dates_use_case),
) -> ClosedDateListSchema:
    views = await use_case.list_closed_dates(ListClosedDatesQuery(ctx=ctx, start=start, end=end))
    return ClosedDateListSchema(items=[ClosedDateSchema.of(v) for v in views])
