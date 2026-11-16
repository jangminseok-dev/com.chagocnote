from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.consent_schema import FormLinkSchema
from customer.adapter.inbound.api.schemas.intake_form_schema import IssueIntakeFormRequestSchema
from customer.app.dtos.issue_intake_form_dto import IssueIntakeFormCommand
from customer.app.ports.input.issue_intake_form_use_case import IssueIntakeFormUseCase
from customer.dependencies.issue_intake_form_provider import get_issue_intake_form_use_case
from hub.app.dtos.shop_context import ShopContext

issue_intake_form_router = APIRouter(prefix="/v1/shops", tags=["forms"])


# 살아 있는 요청이 있으면 그것을 200 으로 돌려준다(같은 링크). 새로 만들었으면 201.
@issue_intake_form_router.post("/{shop_id}/intake-forms", response_model=FormLinkSchema, status_code=201)
async def issue_intake_form(
    body: IssueIntakeFormRequestSchema,
    response: Response,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: IssueIntakeFormUseCase = Depends(get_issue_intake_form_use_case),
) -> FormLinkSchema:
    view = await use_case.issue_intake_form(
        IssueIntakeFormCommand(ctx=ctx, customer_id=body.customer_id, pet_id=body.pet_id))
    if not view.created:
        response.status_code = 200
    return FormLinkSchema.of(view)
