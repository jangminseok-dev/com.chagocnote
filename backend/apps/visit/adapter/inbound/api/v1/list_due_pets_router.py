from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_due_pets_schema import DuePetsSchema
from visit.app.dtos.list_due_pets_dto import ListDuePetsQuery
from visit.app.ports.input.list_due_pets_use_case import ListDuePetsUseCase
from visit.dependencies.list_due_pets_provider import get_list_due_pets_use_case

list_due_pets_router = APIRouter(prefix="/v1/shops", tags=["sales"])


@list_due_pets_router.get("/{shop_id}/sales/due-pets", response_model=DuePetsSchema)
async def list_due_pets(
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    ctx: ShopContext = Depends(require_permission("sales:read")),
    use_case: ListDuePetsUseCase = Depends(get_list_due_pets_use_case),
) -> DuePetsSchema:
    return DuePetsSchema.of(await use_case.list_due_pets(ListDuePetsQuery(ctx=ctx, cursor=cursor)))
