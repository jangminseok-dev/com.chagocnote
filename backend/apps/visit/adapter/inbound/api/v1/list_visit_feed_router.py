from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_visit_feed_schema import VisitFeedSchema
from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery
from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
from visit.dependencies.list_visit_feed_provider import get_list_visit_feed_use_case

list_visit_feed_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_visit_feed_router.get("/{shop_id}/visits/feed", response_model=VisitFeedSchema)
async def list_visit_feed(
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    pet_id: Annotated[int | None, Query(ge=1, le=9_223_372_036_854_775_807)] = None,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListVisitFeedUseCase = Depends(get_list_visit_feed_use_case),
) -> VisitFeedSchema:
    view = await use_case.list_visit_feed(ListVisitFeedQuery(ctx=ctx, cursor=cursor, limit=limit, pet_id=pet_id))
    return VisitFeedSchema.of(view)
