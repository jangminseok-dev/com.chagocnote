from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_visit_slots_schema import VisitSlotsSchema
from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery
from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
from visit.dependencies.list_visit_slots_provider import get_list_visit_slots_use_case

list_visit_slots_router = APIRouter(prefix="/v1/shops", tags=["visits"])

_MAX_BIGINT = 9_223_372_036_854_775_807


@list_visit_slots_router.get("/{shop_id}/visits/slots", response_model=VisitSlotsSchema)
async def list_visit_slots(
    date: date,
    duration: int | None = None,
    at: time | None = None,
    exclude: Annotated[list[Annotated[int, Query(ge=1, le=_MAX_BIGINT)]], Query(max_length=10)] = [],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListVisitSlotsUseCase = Depends(get_list_visit_slots_use_case),
) -> VisitSlotsSchema:
    view = await use_case.list_visit_slots(
        ListVisitSlotsQuery(ctx=ctx, day=date, duration_minutes=duration, at=at, exclude=tuple(exclude))
    )
    return VisitSlotsSchema.of(view)
