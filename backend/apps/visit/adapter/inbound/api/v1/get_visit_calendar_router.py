from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_calendar_schema import VisitCalendarSchema
from visit.app.dtos.get_visit_calendar_dto import GetVisitCalendarQuery
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.dependencies.get_visit_calendar_provider import get_get_visit_calendar_use_case

get_visit_calendar_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_calendar_router.get("/{shop_id}/visits/calendar", response_model=VisitCalendarSchema)
async def get_visit_calendar(
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitCalendarUseCase = Depends(get_get_visit_calendar_use_case),
) -> VisitCalendarSchema:
    year, number = (int(part) for part in month.split("-"))
    view = await use_case.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx, year=year, month=number))
    return VisitCalendarSchema.of(view)
