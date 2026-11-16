from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import AnswerId
from customer.adapter.inbound.api.schemas.intake_answer_schema import IntakeAnswerSchema
from customer.app.dtos.get_intake_answer_dto import GetIntakeAnswerQuery
from customer.app.ports.input.get_intake_answer_use_case import GetIntakeAnswerUseCase
from customer.dependencies.get_intake_answer_provider import get_get_intake_answer_use_case
from hub.app.dtos.shop_context import ShopContext

get_intake_answer_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@get_intake_answer_router.get("/{shop_id}/intake-answers/{answer_id}", response_model=IntakeAnswerSchema)
async def get_intake_answer(
    answer_id: AnswerId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetIntakeAnswerUseCase = Depends(get_get_intake_answer_use_case),
) -> IntakeAnswerSchema:
    return IntakeAnswerSchema.of(await use_case.get_intake_answer(GetIntakeAnswerQuery(ctx=ctx, answer_id=answer_id)))
