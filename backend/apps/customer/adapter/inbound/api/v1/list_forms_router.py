from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.consent_schema import SentFormsSchema
from customer.app.dtos.list_forms_dto import ListFormsQuery
from customer.app.ports.input.list_forms_use_case import ListFormsUseCase
from customer.dependencies.list_forms_provider import get_list_forms_use_case
from hub.app.dtos.shop_context import ShopContext

list_forms_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@list_forms_router.get("/{shop_id}/forms", response_model=SentFormsSchema)
async def list_forms(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListFormsUseCase = Depends(get_list_forms_use_case),
) -> SentFormsSchema:
    return SentFormsSchema.of(await use_case.list_forms(ListFormsQuery(ctx=ctx)))
