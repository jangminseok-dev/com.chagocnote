from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.register_visit_schema import (
    RegisteredVisitsSchema,
    RegisterVisitRequestSchema,
)
from visit.app.dtos.register_visit_dto import RegisterVisitCommand
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.dependencies.register_visit_provider import get_register_visit_use_case

register_visit_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@register_visit_router.post("/{shop_id}/visits", response_model=RegisteredVisitsSchema, status_code=201)
async def register_visit(
    body: RegisterVisitRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: RegisterVisitUseCase = Depends(get_register_visit_use_case),
) -> RegisteredVisitsSchema:
    view = await use_case.register_visit(
        RegisterVisitCommand(
            ctx=ctx, customer_id=body.customer_id, pet_ids=tuple(body.pet_ids), starts_at=body.starts_at,
            duration_minutes=body.duration_minutes, menu_ids=tuple(body.menu_ids),
            memo=body.memo or None, walk_in=body.walk_in,
        )
    )
    return RegisteredVisitsSchema.of(view)
