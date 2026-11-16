from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.intake_question_schema import (
    IntakeQuestionsSchema, UpdateIntakeQuestionsRequestSchema,
)
from customer.app.dtos.update_intake_questions_dto import UpdateIntakeQuestionsCommand
from customer.app.ports.input.update_intake_questions_use_case import UpdateIntakeQuestionsUseCase
from customer.dependencies.update_intake_questions_provider import get_update_intake_questions_use_case
from hub.app.dtos.shop_context import ShopContext

update_intake_questions_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@update_intake_questions_router.put("/{shop_id}/intake-questions", response_model=IntakeQuestionsSchema)
async def update_intake_questions(
    body: UpdateIntakeQuestionsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateIntakeQuestionsUseCase = Depends(get_update_intake_questions_use_case),
) -> IntakeQuestionsSchema:
    questions = await use_case.update_intake_questions(
        UpdateIntakeQuestionsCommand(ctx=ctx, questions=body.to_drafts()))
    return IntakeQuestionsSchema.of(questions)
