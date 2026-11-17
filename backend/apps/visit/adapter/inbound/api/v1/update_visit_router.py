from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.update_visit_schema import UpdatedVisitSchema, UpdateVisitRequestSchema
from visit.app.dtos.update_visit_dto import UpdateVisitCommand
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.dependencies.update_visit_provider import get_update_visit_use_case

update_visit_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_visit_router.put("/{shop_id}/visits/{visit_id}", response_model=UpdatedVisitSchema)
async def update_visit(
    visit_id: VisitId,
    body: UpdateVisitRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: UpdateVisitUseCase = Depends(get_update_visit_use_case),
) -> UpdatedVisitSchema:
    view = await use_case.update_visit(
        UpdateVisitCommand(
            ctx=ctx, visit_id=visit_id, starts_at=body.starts_at, pet_id=body.pet_id,
            duration_minutes=body.duration_minutes, menu_ids=tuple(body.menu_ids), memo=body.memo or None,
            scope=body.scope, family=body.family, skip_visit_ids=tuple(body.skip_visit_ids),
        )
    )
    return UpdatedVisitSchema.of(view)
