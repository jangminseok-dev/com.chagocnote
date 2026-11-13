from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_sales_goal_schema import SalesGoalSchema
from visit.adapter.inbound.api.schemas.update_sales_goal_schema import UpdateSalesGoalRequestSchema
from visit.app.dtos.update_sales_goal_dto import UpdateSalesGoalCommand
from visit.app.ports.input.update_sales_goal_use_case import UpdateSalesGoalUseCase
from visit.dependencies.update_sales_goal_provider import get_update_sales_goal_use_case

update_sales_goal_router = APIRouter(prefix="/v1/shops", tags=["sales"])


@update_sales_goal_router.put("/{shop_id}/sales/goal", response_model=SalesGoalSchema)
async def update_sales_goal(
    body: UpdateSalesGoalRequestSchema,
    # 목표는 매출을 보는 사람(사장)이 정한다 — 새 권한을 만들지 않았다(설계 ⑧ 3.5).
    ctx: ShopContext = Depends(require_permission("sales:read")),
    use_case: UpdateSalesGoalUseCase = Depends(get_update_sales_goal_use_case),
) -> SalesGoalSchema:
    view = await use_case.update_sales_goal(
        UpdateSalesGoalCommand(ctx=ctx, monthly_amount=body.monthly_amount)
    )
    return SalesGoalSchema.of(view)
