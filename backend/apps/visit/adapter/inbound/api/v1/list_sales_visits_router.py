from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_sales_visits_schema import SalesVisitsSchema
from visit.app.dtos.list_sales_visits_dto import ListSalesVisitsQuery
from visit.app.ports.input.list_sales_visits_use_case import ListSalesVisitsUseCase
from visit.dependencies.list_sales_visits_provider import get_list_sales_visits_use_case

list_sales_visits_router = APIRouter(prefix="/v1/shops", tags=["sales"])


@list_sales_visits_router.get("/{shop_id}/sales/visits", response_model=SalesVisitsSchema)
async def list_sales_visits(
    span: Annotated[Literal["day", "week", "month", "year"], Query()],
    filter: Annotated[Literal["unrecorded", "no_show", "canceled", "menu"], Query()],
    anchor: Annotated[date | None, Query()] = None,
    menu_id: Annotated[int | None, Query(ge=1, le=9_223_372_036_854_775_807)] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    ctx: ShopContext = Depends(require_permission("sales:read")),
    use_case: ListSalesVisitsUseCase = Depends(get_list_sales_visits_use_case),
) -> SalesVisitsSchema:
    view = await use_case.list_sales_visits(ListSalesVisitsQuery(
        ctx=ctx, span=span, anchor=anchor, filter=filter, menu_id=menu_id, cursor=cursor,
    ))
    return SalesVisitsSchema.of(view)
