from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_checks_schema import VisitChecksSchema
from visit.app.dtos.get_visit_checks_dto import GetVisitChecksQuery
from visit.app.ports.input.get_visit_checks_use_case import GetVisitChecksUseCase
from visit.dependencies.get_visit_checks_provider import get_get_visit_checks_use_case

get_visit_checks_router = APIRouter(prefix="/v1/shops", tags=["visits"])

_MAX_BIGINT = 9_223_372_036_854_775_807
_Id = Annotated[int, Query(ge=1, le=_MAX_BIGINT)]


@get_visit_checks_router.get("/{shop_id}/visit-checks", response_model=VisitChecksSchema)
async def get_visit_checks(
    customer_id: _Id,
    date: date,
    # 같은 이름을 되풀이해 여러 마리를 준다(?pet_ids=1&pet_ids=2). 없으면 보호자만의 예약이다.
    pet_ids: Annotated[list[Annotated[int, Query(ge=1, le=_MAX_BIGINT)]], Query(max_length=10)] = [],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitChecksUseCase = Depends(get_get_visit_checks_use_case),
) -> VisitChecksSchema:
    view = await use_case.get_visit_checks(
        GetVisitChecksQuery(ctx=ctx, customer_id=customer_id, pet_ids=tuple(pet_ids), day=date)
    )
    return VisitChecksSchema.of(view)
