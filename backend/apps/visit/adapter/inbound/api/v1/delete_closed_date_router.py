from datetime import date

from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand
from visit.app.ports.input.delete_closed_date_use_case import DeleteClosedDateUseCase
from visit.dependencies.delete_closed_date_provider import get_delete_closed_date_use_case

delete_closed_date_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@delete_closed_date_router.delete("/{shop_id}/closed-dates/{day}", status_code=204)
async def delete_closed_date(
    day: date,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: DeleteClosedDateUseCase = Depends(get_delete_closed_date_use_case),
) -> Response:
    await use_case.delete_closed_date(DeleteClosedDateCommand(ctx=ctx, day=day))
    return Response(status_code=204)
