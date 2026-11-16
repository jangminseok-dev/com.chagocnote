from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.intake_answer_schema import IntakeAnswersSchema
from customer.app.dtos.list_intake_answers_dto import ListIntakeAnswersQuery
from customer.app.ports.input.list_intake_answers_use_case import ListIntakeAnswersUseCase
from customer.dependencies.list_intake_answers_provider import get_list_intake_answers_use_case
from hub.app.dtos.shop_context import ShopContext

list_intake_answers_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@list_intake_answers_router.get("/{shop_id}/intake-answers", response_model=IntakeAnswersSchema)
async def list_intake_answers(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListIntakeAnswersUseCase = Depends(get_list_intake_answers_use_case),
) -> IntakeAnswersSchema:
    return IntakeAnswersSchema.of(await use_case.list_intake_answers(ListIntakeAnswersQuery(ctx=ctx)))
