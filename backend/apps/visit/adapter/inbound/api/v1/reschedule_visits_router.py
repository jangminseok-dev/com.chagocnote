from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.reschedule_visits_schema import (
    RescheduledVisitsSchema,
    RescheduleVisitsRequestSchema,
)
from visit.app.dtos.reschedule_visits_dto import RescheduleVisitsCommand
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.dependencies.reschedule_visits_provider import get_reschedule_visits_use_case

reschedule_visits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@reschedule_visits_router.post("/{shop_id}/visits/reschedule", response_model=RescheduledVisitsSchema)
async def reschedule_visits(
    body: RescheduleVisitsRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: RescheduleVisitsUseCase = Depends(get_reschedule_visits_use_case),
) -> RescheduledVisitsSchema:
    view = await use_case.reschedule_visits(
        RescheduleVisitsCommand(ctx=ctx, visit_ids=tuple(body.visit_ids), starts_at=body.starts_at, scope=body.scope,
                                family=body.family, skip_visit_ids=tuple(body.skip_visit_ids))
    )
    return RescheduledVisitsSchema.of(view)
