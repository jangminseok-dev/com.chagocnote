from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.transition_visits_schema import (
    TransitionedVisitsSchema,
    TransitionVisitsRequestSchema,
)
from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.dependencies.transition_visits_provider import get_transition_visits_use_case

transition_visits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@transition_visits_router.post("/{shop_id}/visits/transitions", response_model=TransitionedVisitsSchema)
async def transition_visits(
    body: TransitionVisitsRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: TransitionVisitsUseCase = Depends(get_transition_visits_use_case),
) -> TransitionedVisitsSchema:
    view = await use_case.transition_visits(
        TransitionVisitsCommand(ctx=ctx, visit_ids=tuple(body.visit_ids), action=body.action,
                                cancel_reason=body.cancel_reason)
    )
    return TransitionedVisitsSchema.of(view)
