from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import AnswerId
from customer.app.dtos.delete_intake_answer_dto import DeleteIntakeAnswerCommand
from customer.app.ports.input.delete_intake_answer_use_case import DeleteIntakeAnswerUseCase
from customer.dependencies.delete_intake_answer_provider import get_delete_intake_answer_use_case
from hub.app.dtos.shop_context import ShopContext

delete_intake_answer_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@delete_intake_answer_router.delete("/{shop_id}/intake-answers/{answer_id}", status_code=204)
async def delete_intake_answer(
    answer_id: AnswerId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: DeleteIntakeAnswerUseCase = Depends(get_delete_intake_answer_use_case),
) -> Response:
    await use_case.delete_intake_answer(DeleteIntakeAnswerCommand(ctx=ctx, answer_id=answer_id))
    return Response(status_code=204)
