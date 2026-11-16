from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_revisits_schema import RevisitsSchema
from visit.app.dtos.list_revisits_dto import ListRevisitsQuery
from visit.app.ports.input.list_revisits_use_case import ListRevisitsUseCase
from visit.dependencies.list_revisits_provider import get_list_revisits_use_case

list_revisits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_revisits_router.get("/{shop_id}/revisits", response_model=RevisitsSchema)
async def list_revisits(
    bucket: Literal["soon", "due"],
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListRevisitsUseCase = Depends(get_list_revisits_use_case),
) -> RevisitsSchema:
    return RevisitsSchema.of(await use_case.list_revisits(ListRevisitsQuery(ctx=ctx, bucket=bucket, cursor=cursor)))
