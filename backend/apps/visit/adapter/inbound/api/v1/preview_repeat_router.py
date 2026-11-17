from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.preview_repeat_schema import RepeatPreviewSchema
from visit.app.dtos.preview_repeat_dto import PreviewRepeatQuery
from visit.app.ports.input.preview_repeat_use_case import PreviewRepeatUseCase
from visit.dependencies.preview_repeat_provider import get_preview_repeat_use_case
from visit.domain.services.visit_series import MAX_COUNT, MAX_INTERVAL_WEEKS, MIN_COUNT, MIN_INTERVAL_WEEKS

preview_repeat_router = APIRouter(prefix="/v1/shops", tags=["visits"])

_MAX_BIGINT = 9_223_372_036_854_775_807
_Id = Annotated[int, Query(ge=1, le=_MAX_BIGINT)]
_Ids = Annotated[list[Annotated[int, Query(ge=1, le=_MAX_BIGINT)]], Query(max_length=10)]


@preview_repeat_router.get("/{shop_id}/visits/repeat-preview", response_model=RepeatPreviewSchema)
async def preview_repeat(
    customer_id: _Id,
    starts_at: Annotated[AwareDatetime, Query()],
    interval_weeks: Annotated[int, Query(ge=MIN_INTERVAL_WEEKS, le=MAX_INTERVAL_WEEKS)],
    count: Annotated[int, Query(ge=MIN_COUNT, le=MAX_COUNT)],
    duration_minutes: Annotated[int | None, Query()] = None,
    pet_ids: _Ids = [],
    menu_ids: _Ids = [],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: PreviewRepeatUseCase = Depends(get_preview_repeat_use_case),
) -> RepeatPreviewSchema:
    view = await use_case.preview_repeat(PreviewRepeatQuery(
        ctx=ctx, customer_id=customer_id, pet_ids=tuple(dict.fromkeys(pet_ids)), starts_at=starts_at,
        duration_minutes=duration_minutes, menu_ids=tuple(dict.fromkeys(menu_ids)), interval_weeks=interval_weeks,
        count=count))
    return RepeatPreviewSchema.of(view)
