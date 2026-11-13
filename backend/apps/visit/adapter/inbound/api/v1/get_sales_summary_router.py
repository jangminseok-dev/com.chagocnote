from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_sales_summary_schema import SalesSummarySchema
from visit.app.dtos.get_sales_summary_dto import GetSalesSummaryQuery
from visit.app.ports.input.get_sales_summary_use_case import GetSalesSummaryUseCase
from visit.dependencies.get_sales_summary_provider import get_get_sales_summary_use_case

get_sales_summary_router = APIRouter(prefix="/v1/shops", tags=["sales"])


@get_sales_summary_router.get("/{shop_id}/sales/summary", response_model=SalesSummarySchema)
async def get_sales_summary(
    span: Annotated[Literal["day", "week", "month", "year"], Query()],
    anchor: Annotated[date | None, Query()] = None,
    ctx: ShopContext = Depends(require_permission("sales:read")),
    use_case: GetSalesSummaryUseCase = Depends(get_get_sales_summary_use_case),
) -> SalesSummarySchema:
    view = await use_case.get_sales_summary(GetSalesSummaryQuery(ctx=ctx, span=span, anchor=anchor))
    return SalesSummarySchema.of(view)
