from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.intake_question_schema import IntakeQuestionsSchema
from customer.app.dtos.list_intake_questions_dto import ListIntakeQuestionsQuery
from customer.app.ports.input.list_intake_questions_use_case import ListIntakeQuestionsUseCase
from customer.dependencies.list_intake_questions_provider import get_list_intake_questions_use_case
from hub.app.dtos.shop_context import ShopContext

list_intake_questions_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@list_intake_questions_router.get("/{shop_id}/intake-questions", response_model=IntakeQuestionsSchema)
async def list_intake_questions(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListIntakeQuestionsUseCase = Depends(get_list_intake_questions_use_case),
) -> IntakeQuestionsSchema:
    return IntakeQuestionsSchema.of(await use_case.list_intake_questions(ListIntakeQuestionsQuery(ctx=ctx)))
