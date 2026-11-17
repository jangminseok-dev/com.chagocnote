from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import SeriesId
from visit.adapter.inbound.api.schemas.get_visit_series_schema import VisitSeriesSchema
from visit.app.dtos.get_visit_series_dto import GetVisitSeriesQuery
from visit.app.ports.input.get_visit_series_use_case import GetVisitSeriesUseCase
from visit.dependencies.get_visit_series_provider import get_get_visit_series_use_case

get_visit_series_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_series_router.get("/{shop_id}/visit-series/{series_id}", response_model=VisitSeriesSchema)
async def get_visit_series(
    series_id: SeriesId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitSeriesUseCase = Depends(get_get_visit_series_use_case),
) -> VisitSeriesSchema:
    return VisitSeriesSchema.of(await use_case.get_visit_series(GetVisitSeriesQuery(ctx=ctx, series_id=series_id)))
