from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.add_closed_date_schema import AddClosedDateRequestSchema
from visit.adapter.inbound.api.schemas.list_closed_dates_schema import ClosedDateSchema
from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.ports.input.add_closed_date_use_case import AddClosedDateUseCase
from visit.dependencies.add_closed_date_provider import get_add_closed_date_use_case

add_closed_date_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@add_closed_date_router.post("/{shop_id}/closed-dates", response_model=ClosedDateSchema)
async def add_closed_date(
    body: AddClosedDateRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: AddClosedDateUseCase = Depends(get_add_closed_date_use_case),
) -> ClosedDateSchema:
    view = await use_case.add_closed_date(
        AddClosedDateCommand(ctx=ctx, day=body.date, note=body.note or None)
    )
    return ClosedDateSchema.of(view)
