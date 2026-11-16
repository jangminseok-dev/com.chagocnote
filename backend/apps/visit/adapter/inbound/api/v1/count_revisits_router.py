from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_revisits_schema import RevisitCountsSchema
from visit.app.dtos.count_revisits_dto import CountRevisitsQuery
from visit.app.ports.input.count_revisits_use_case import CountRevisitsUseCase
from visit.dependencies.count_revisits_provider import get_count_revisits_use_case

count_revisits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@count_revisits_router.get("/{shop_id}/revisits/counts", response_model=RevisitCountsSchema)
async def count_revisits(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: CountRevisitsUseCase = Depends(get_count_revisits_use_case),
) -> RevisitCountsSchema:
    return RevisitCountsSchema.of(await use_case.count_revisits(CountRevisitsQuery(ctx=ctx)))
