from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_defaults_schema import VisitDefaultsSchema
from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery
from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
from visit.dependencies.get_visit_defaults_provider import get_get_visit_defaults_use_case

get_visit_defaults_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_defaults_router.get("/{shop_id}/visits/defaults", response_model=VisitDefaultsSchema)
async def get_visit_defaults(
    pet_id: Annotated[int, Query(ge=1, le=9_223_372_036_854_775_807)],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitDefaultsUseCase = Depends(get_get_visit_defaults_use_case),
) -> VisitDefaultsSchema:
    return VisitDefaultsSchema.of(
        await use_case.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx, pet_id=pet_id))
    )
