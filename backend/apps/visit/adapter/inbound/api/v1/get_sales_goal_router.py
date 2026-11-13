from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_sales_goal_schema import SalesGoalSchema
from visit.app.dtos.get_sales_goal_dto import GetSalesGoalQuery
from visit.app.ports.input.get_sales_goal_use_case import GetSalesGoalUseCase
from visit.dependencies.get_sales_goal_provider import get_get_sales_goal_use_case

get_sales_goal_router = APIRouter(prefix="/v1/shops", tags=["sales"])


@get_sales_goal_router.get("/{shop_id}/sales/goal", response_model=SalesGoalSchema)
async def get_sales_goal(
    ctx: ShopContext = Depends(require_permission("sales:read")),
    use_case: GetSalesGoalUseCase = Depends(get_get_sales_goal_use_case),
) -> SalesGoalSchema:
    return SalesGoalSchema.of(await use_case.get_sales_goal(GetSalesGoalQuery(ctx=ctx)))
